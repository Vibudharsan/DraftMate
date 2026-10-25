package com.draftmate.app;

import android.Manifest;
import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.ContentValues;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.Typeface;
import android.net.Uri;
import android.net.http.SslCertificate;
import android.net.http.SslError;
import android.os.Bundle;
import android.provider.MediaStore;
import android.speech.tts.TextToSpeech;
import android.text.InputType;
import android.util.Base64;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.webkit.JavascriptInterface;
import android.webkit.MimeTypeMap;
import android.webkit.PermissionRequest;
import android.webkit.SslErrorHandler;
import android.webkit.URLUtil;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import java.io.InputStream;
import java.io.OutputStream;
import java.net.URL;
import java.security.KeyStore;
import java.security.cert.CertificateFactory;
import java.security.cert.X509Certificate;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

import javax.net.ssl.HttpsURLConnection;
import javax.net.ssl.SSLContext;
import javax.net.ssl.TrustManagerFactory;

/**
 * DraftMate for Android: a full-screen window onto the DraftMate server running on a computer on the same Wi-Fi.
 * The server's local certificate authority is bundled, so no certificate setup is needed on the phone; only
 * certificates signed by that CA are accepted. Bridges what a WebView lacks: microphone permission, file picking,
 * saving downloads and text-to-speech.
 */
public class MainActivity extends Activity {
    private static final int REQUEST_FILES = 1, REQUEST_MIC = 2;
    private static final String TTS_POLYFILL = "(function(){if(window.__dmTts||!window.DraftMateAndroid)return;window.__dmTts=1;"
            + "window.SpeechSynthesisUtterance=function(t){this.text=t||'';this.lang='';this.pitch=1;this.rate=1;this.voice=null;};"
            + "var s={speak:function(u){DraftMateAndroid.speak(String(u.text||''),u.lang||'en-IN',u.pitch||1,u.rate||1)},"
            + "cancel:function(){DraftMateAndroid.stopSpeaking()},pause:function(){},resume:function(){},getVoices:function(){return []},"
            + "get speaking(){return DraftMateAndroid.isSpeaking()}};"
            + "try{Object.defineProperty(window,'speechSynthesis',{value:s,configurable:true})}catch(e){window.speechSynthesis=s}})();";

    private WebView web;
    private LinearLayout setup;
    private TextView status;
    private EditText address;
    private String server;
    private X509Certificate ca;
    private SSLContext trusted;
    private TextToSpeech tts;
    private ValueCallback<Uri[]> fileCallback;
    private PermissionRequest pendingPermission;
    private SharedPreferences prefs;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(Color.rgb(19, 46, 41));
        getWindow().setNavigationBarColor(Color.rgb(19, 46, 41));
        prefs = getSharedPreferences("draftmate", MODE_PRIVATE);
        try {
            loadCertificateAuthority();
        } catch (Exception e) {
            Toast.makeText(this, "Bundled certificate missing: " + e.getMessage(), Toast.LENGTH_LONG).show();
        }
        tts = new TextToSpeech(this, s -> { });
        FrameLayout root = new FrameLayout(this);
        root.addView(createWebView(), new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        root.addView(createSetup(), new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        setContentView(root);
        findServer(prefs.getString("server", null));
    }

    private void loadCertificateAuthority() throws Exception {
        try (InputStream in = getAssets().open("draftmate_ca.pem")) {
            ca = (X509Certificate) CertificateFactory.getInstance("X.509").generateCertificate(in);
        }
        KeyStore store = KeyStore.getInstance(KeyStore.getDefaultType());
        store.load(null, null);
        store.setCertificateEntry("draftmate", ca);
        TrustManagerFactory factory = TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm());
        factory.init(store);
        trusted = SSLContext.getInstance("TLS");
        trusted.init(null, factory.getTrustManagers(), null);
    }

    // ---- Finding the DraftMate computer ----

    private static String normalise(String input) {
        String value = input == null ? "" : input.trim();
        if (value.isEmpty()) return null;
        if (!value.contains("://")) value = "https://" + value;
        Uri uri = Uri.parse(value);
        if (uri.getHost() == null) return null;
        return "https://" + uri.getHost() + ":" + (uri.getPort() > 0 ? uri.getPort() : 4175);
    }

    private boolean reachable(String base) {
        if (trusted == null) return false;
        HttpsURLConnection connection = null;
        try {
            connection = (HttpsURLConnection) new URL(base + "/manifest.webmanifest").openConnection();
            connection.setSSLSocketFactory(trusted.getSocketFactory());
            connection.setConnectTimeout(2500);
            connection.setReadTimeout(2500);
            return connection.getResponseCode() == 200;
        } catch (Exception e) {
            return false;
        } finally {
            if (connection != null) connection.disconnect();
        }
    }

    private void findServer(String preferred) {
        showSetup("Looking for DraftMate on this Wi-Fi…", false);
        List<String> candidates = new ArrayList<>();
        String first = normalise(preferred);
        if (first != null) candidates.add(first);
        for (String host : Defaults.HOSTS) if (!candidates.contains(host)) candidates.add(host);
        new Thread(() -> {
            for (String candidate : candidates) {
                if (reachable(candidate)) {
                    runOnUiThread(() -> open(candidate));
                    return;
                }
            }
            runOnUiThread(() -> showSetup("Couldn't reach DraftMate. Make sure Start-DraftMate-WiFi.cmd is running on the computer and this phone is on the same Wi-Fi, then enter the address it shows.", true));
        }).start();
    }

    private void open(String base) {
        server = base;
        prefs.edit().putString("server", base).apply();
        setup.setVisibility(View.GONE);
        web.setVisibility(View.VISIBLE);
        web.loadUrl(base + "/#overview");
    }

    private boolean sameOrigin(Uri uri) {
        if (server == null || uri == null) return false;
        Uri base = Uri.parse(server);
        return "https".equals(uri.getScheme()) && base.getHost().equals(uri.getHost()) && base.getPort() == (uri.getPort() > 0 ? uri.getPort() : 443);
    }

    private boolean signedByDraftMate(SslCertificate certificate) {
        if (ca == null || certificate == null) return false;
        X509Certificate leaf = certificate.getX509Certificate();
        if (leaf == null) return false;
        try {
            leaf.checkValidity();
            leaf.verify(ca.getPublicKey());
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    // ---- Screens ----

    private View createSetup() {
        setup = new LinearLayout(this);
        setup.setOrientation(LinearLayout.VERTICAL);
        setup.setGravity(Gravity.CENTER);
        setup.setBackgroundColor(Color.rgb(19, 46, 41));
        int pad = dp(28);
        setup.setPadding(pad, pad, pad, pad);
        TextView title = new TextView(this);
        title.setText("DraftMate");
        title.setTextColor(Color.rgb(231, 239, 218));
        title.setTextSize(32);
        title.setTypeface(Typeface.SERIF, Typeface.BOLD);
        title.setGravity(Gravity.CENTER);
        setup.addView(title);
        status = new TextView(this);
        status.setTextColor(Color.rgb(185, 201, 189));
        status.setTextSize(15);
        status.setGravity(Gravity.CENTER);
        status.setPadding(0, dp(14), 0, dp(18));
        setup.addView(status);
        address = new EditText(this);
        address.setHint("Computer address, e.g. 192.168.1.5");
        address.setSingleLine(true);
        address.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        address.setTextColor(Color.WHITE);
        address.setHintTextColor(Color.rgb(140, 160, 150));
        setup.addView(address, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        Button connect = new Button(this);
        connect.setText("Connect");
        connect.setOnClickListener(v -> findServer(address.getText().toString()));
        setup.addView(connect, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        return setup;
    }

    private void showSetup(String message, boolean askForAddress) {
        status.setText(message);
        address.setVisibility(askForAddress ? View.VISIBLE : View.GONE);
        for (int i = 0; i < setup.getChildCount(); i++) if (setup.getChildAt(i) instanceof Button) setup.getChildAt(i).setVisibility(askForAddress ? View.VISIBLE : View.GONE);
        if (askForAddress && server != null) address.setText(Uri.parse(server).getHost());
        setup.setVisibility(View.VISIBLE);
        web.setVisibility(View.GONE);
    }

    private View createWebView() {
        web = new WebView(this);
        web.setVisibility(View.GONE);
        WebSettings settings = web.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        settings.setSupportMultipleWindows(false);
        settings.setUserAgentString(settings.getUserAgentString() + " DraftMateApp/1.0");
        web.addJavascriptInterface(new Bridge(), "DraftMateAndroid");
        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                if (sameOrigin(request.getUrl())) return false;
                openExternally(request.getUrl());
                return true;
            }

            @Override
            public void onReceivedSslError(WebView view, SslErrorHandler handler, SslError error) {
                // Accept only the DraftMate server's own certificate; anything else is refused.
                if (signedByDraftMate(error.getCertificate())) handler.proceed();
                else handler.cancel();
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                view.evaluateJavascript(TTS_POLYFILL, null);
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame()) showSetup("Lost the connection to DraftMate. Check the computer and Wi-Fi, then reconnect.", true);
            }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onPermissionRequest(PermissionRequest request) {
                for (String resource : request.getResources()) {
                    if (PermissionRequest.RESOURCE_AUDIO_CAPTURE.equals(resource)) {
                        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
                            request.grant(new String[]{PermissionRequest.RESOURCE_AUDIO_CAPTURE});
                        } else {
                            pendingPermission = request;
                            requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, REQUEST_MIC);
                        }
                        return;
                    }
                }
                request.deny();
            }

            @Override
            public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback, FileChooserParams params) {
                if (fileCallback != null) fileCallback.onReceiveValue(null);
                fileCallback = callback;
                try {
                    startActivityForResult(params.createIntent(), REQUEST_FILES);
                    return true;
                } catch (ActivityNotFoundException e) {
                    fileCallback = null;
                    return false;
                }
            }
        });
        web.setDownloadListener((url, userAgent, disposition, mime, length) -> {
            Uri uri = Uri.parse(url);
            if (!url.startsWith("blob:") && !sameOrigin(uri)) {
                openExternally(uri);
                return;
            }
            String name = url.startsWith("blob:") ? "DraftMate-" + System.currentTimeMillis() + extension(mime) : URLUtil.guessFileName(url, disposition, mime);
            // Fetch inside the page (it can read blob: URLs and already trusts the server), then hand the bytes to Java.
            String script = "fetch(" + quote(url) + ").then(r=>r.blob()).then(b=>new Promise(res=>{const f=new FileReader();f.onload=()=>res(f.result);f.readAsDataURL(b)}))"
                    + ".then(d=>DraftMateAndroid.saveFile(String(d).split(',')[1]||'',"
                    + quote(mime == null ? "" : mime) + "," + quote(name) + ")).catch(()=>DraftMateAndroid.saveFailed())";
            web.evaluateJavascript(script, null);
        });
        return web;
    }

    private void openExternally(Uri uri) {
        try {
            startActivity(new Intent(Intent.ACTION_VIEW, uri));
        } catch (ActivityNotFoundException e) {
            Toast.makeText(this, "No app can open this link.", Toast.LENGTH_SHORT).show();
        }
    }

    private static String extension(String mime) {
        String ext = mime == null ? null : MimeTypeMap.getSingleton().getExtensionFromMimeType(mime);
        return ext == null ? ".txt" : "." + ext;
    }

    private static String quote(String value) {
        return "'" + value.replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ") + "'";
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    /** Methods callable from the page as window.DraftMateAndroid. Only the DraftMate server's pages are loaded. */
    private class Bridge {
        @JavascriptInterface
        public void speak(String text, String lang, float pitch, float rate) {
            if (tts == null) return;
            tts.setLanguage(Locale.forLanguageTag(lang == null || lang.isEmpty() ? "en-IN" : lang));
            tts.setPitch(pitch);
            tts.setSpeechRate(rate);
            tts.speak(text, TextToSpeech.QUEUE_ADD, null, "dm" + System.nanoTime());
        }

        @JavascriptInterface
        public void stopSpeaking() {
            if (tts != null) tts.stop();
        }

        @JavascriptInterface
        public boolean isSpeaking() {
            return tts != null && tts.isSpeaking();
        }

        @JavascriptInterface
        public void saveFile(String base64, String mime, String name) {
            try {
                byte[] bytes = Base64.decode(base64, Base64.DEFAULT);
                ContentValues values = new ContentValues();
                values.put(MediaStore.Downloads.DISPLAY_NAME, name);
                values.put(MediaStore.Downloads.MIME_TYPE, mime == null || mime.isEmpty() ? "application/octet-stream" : mime);
                values.put(MediaStore.Downloads.RELATIVE_PATH, "Download/DraftMate");
                Uri target = getContentResolver().insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values);
                if (target == null) throw new IllegalStateException();
                try (OutputStream out = getContentResolver().openOutputStream(target)) {
                    out.write(bytes);
                }
                runOnUiThread(() -> Toast.makeText(MainActivity.this, "Saved to Downloads/DraftMate: " + name, Toast.LENGTH_LONG).show());
            } catch (Exception e) {
                saveFailed();
            }
        }

        @JavascriptInterface
        public void saveFailed() {
            runOnUiThread(() -> Toast.makeText(MainActivity.this, "Could not save the file.", Toast.LENGTH_SHORT).show());
        }
    }

    @Override
    protected void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request, result, data);
        if (request == REQUEST_FILES && fileCallback != null) {
            fileCallback.onReceiveValue(WebChromeClient.FileChooserParams.parseResult(result, data));
            fileCallback = null;
        }
    }

    @Override
    public void onRequestPermissionsResult(int request, String[] permissions, int[] results) {
        if (request == REQUEST_MIC && pendingPermission != null) {
            if (results.length > 0 && results[0] == PackageManager.PERMISSION_GRANTED) pendingPermission.grant(new String[]{PermissionRequest.RESOURCE_AUDIO_CAPTURE});
            else pendingPermission.deny();
            pendingPermission = null;
        }
    }

    @Override
    public void onBackPressed() {
        if (web.getVisibility() == View.VISIBLE && web.canGoBack()) web.goBack();
        else super.onBackPressed();
    }

    @Override
    protected void onDestroy() {
        if (tts != null) tts.shutdown();
        web.destroy();
        super.onDestroy();
    }
}
