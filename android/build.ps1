# Builds DraftMate.apk without Android Studio or Gradle: aapt2 -> javac -> d8 -> zipalign -> apksigner.
# Requires the Android SDK at ..\..\..\android-sdk (platforms;android-36, build-tools;36.1.0) and a JDK 17+.
$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
$web = Split-Path $here -Parent
$sdk = if ($env:ANDROID_HOME) { $env:ANDROID_HOME } else { 'C:\TEST_APP\android-sdk' }
$bt = Join-Path $sdk 'build-tools\36.1.0'
$jar = Join-Path $sdk 'platforms\android-36\android.jar'
if (-not $env:JAVA_HOME) { $env:JAVA_HOME = 'C:\Program Files\Microsoft\jdk-21.0.10.7-hotspot' }
$java = Join-Path $env:JAVA_HOME 'bin'
$build = Join-Path $here 'build'
function Run($exe) { & $exe @args; if ($LASTEXITCODE -ne 0) { throw "$exe failed ($LASTEXITCODE)" } }

if (Test-Path $build) { Remove-Item $build -Recurse -Force }
New-Item -ItemType Directory -Force $build, "$build\classes", "$build\dex" | Out-Null
Run (Join-Path $web '.venv\Scripts\python.exe') (Join-Path $here 'prepare.py')

Run "$bt\aapt2.exe" compile --dir "$here\res" -o "$build\res.zip"
Run "$bt\aapt2.exe" link -I $jar --manifest "$here\AndroidManifest.xml" -A "$build\assets" -o "$build\base.apk" "$build\res.zip" --min-sdk-version 29 --target-sdk-version 34 --version-code 1 --version-name 1.0

$sources = @(Get-ChildItem "$here\src", "$build\gen" -Recurse -Filter *.java | ForEach-Object FullName)
Run "$java\javac.exe" --release 11 -nowarn -encoding UTF-8 -classpath $jar -d "$build\classes" @sources
$classes = @(Get-ChildItem "$build\classes" -Recurse -Filter *.class | ForEach-Object FullName)
Run "$bt\d8.bat" --release --min-api 29 --lib $jar --output "$build\dex" @classes

# Add classes.dex to the resource APK.
Copy-Item "$build\base.apk" "$build\unsigned.apk"
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::Open("$build\unsigned.apk", 'Update')
[System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, "$build\dex\classes.dex", 'classes.dex') | Out-Null
$zip.Dispose()
Run "$bt\zipalign.exe" -p -f 4 "$build\unsigned.apk" "$build\aligned.apk"

# Signing key stays on this computer. Keep it: future updates must be signed with the same key.
$ks = Join-Path $here 'draftmate-release.keystore'
if (-not (Test-Path $ks)) {
  Run "$java\keytool.exe" -genkeypair -keystore $ks -alias draftmate -keyalg EC -groupname secp256r1 -validity 10000 -storepass draftmate -keypass draftmate -dname 'CN=DraftMate, O=DraftMate local'
}
Run "$bt\apksigner.bat" sign --ks $ks --ks-key-alias draftmate --ks-pass pass:draftmate --key-pass pass:draftmate --out "$build\DraftMate.apk" "$build\aligned.apk"
Run "$bt\apksigner.bat" verify "$build\DraftMate.apk"
Write-Output ("Built " + "$build\DraftMate.apk" + " (" + [math]::Round((Get-Item "$build\DraftMate.apk").Length / 1KB) + " KB)")
