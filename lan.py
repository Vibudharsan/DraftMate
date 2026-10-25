"""Wi-Fi sharing helpers: local addresses and HTTPS certificates.

A small local certificate authority (CA) signs the server certificate. Installing the CA on a phone makes the
Wi-Fi address a trusted secure origin, so DraftMate installs as a home-screen app with no warning. The CA is
name-constrained to private network addresses and localhost, so it cannot vouch for any public website.
"""
from pathlib import Path
import socket, ipaddress, datetime, json
DATA=Path(__file__).resolve().parent/'data'
CA_CERT,CA_KEY=DATA/'lan-ca.pem',DATA/'lan-ca-key.pem'
PRIVATE_NETS=['10.0.0.0/8','172.16.0.0/12','192.168.0.0/16','127.0.0.0/8']

def lan_ips():
 found=set()
 try:
  with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
   s.connect(('10.255.255.255',1));found.add(s.getsockname()[0])  # no packet is sent; picks the outward interface
 except OSError:pass
 try:found.update(socket.gethostbyname_ex(socket.gethostname())[2])
 except OSError:pass
 return sorted(ip for ip in found if ipaddress.ip_address(ip).is_private and not ip.startswith(('127.','169.254.')))

def _crypto():
 from cryptography import x509
 from cryptography.x509.oid import NameOID,ExtendedKeyUsageOID
 from cryptography.hazmat.primitives import hashes,serialization
 from cryptography.hazmat.primitives.asymmetric import ec
 return x509,NameOID,ExtendedKeyUsageOID,hashes,serialization,ec

def _write_key(path,key):
 _,_,_,_,serialization,_=_crypto()
 path.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))

def ensure_ca():
 x509,NameOID,_,hashes,serialization,ec=_crypto()
 if CA_CERT.exists() and CA_KEY.exists():
  return x509.load_pem_x509_certificate(CA_CERT.read_bytes()),serialization.load_pem_private_key(CA_KEY.read_bytes(),None)
 key=ec.generate_private_key(ec.SECP256R1());now=datetime.datetime.now(datetime.timezone.utc)
 name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'DraftMate local network CA'),x509.NameAttribute(NameOID.ORGANIZATION_NAME,'DraftMate (this computer only)')])
 permitted=[x509.IPAddress(ipaddress.ip_network(n)) for n in PRIVATE_NETS]+[x509.DNSName('localhost')]
 cert=(x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key()).serial_number(x509.random_serial_number())
  .not_valid_before(now-datetime.timedelta(days=1)).not_valid_after(now+datetime.timedelta(days=3650))
  .add_extension(x509.BasicConstraints(ca=True,path_length=0),critical=True)
  .add_extension(x509.KeyUsage(digital_signature=True,key_cert_sign=True,crl_sign=True,content_commitment=False,key_encipherment=False,data_encipherment=False,key_agreement=False,encipher_only=False,decipher_only=False),critical=True)
  .add_extension(x509.NameConstraints(permitted_subtrees=permitted,excluded_subtrees=None),critical=True)
  .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()),critical=False)
  .sign(key,hashes.SHA256()))
 DATA.mkdir(exist_ok=True);_write_key(CA_KEY,key);CA_CERT.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
 return cert,key

def ensure_cert(ips):
 """Reuse the server certificate while it covers the current addresses; re-sign it with the CA when they change."""
 cert_path,key_path,meta=DATA/'lan-cert.pem',DATA/'lan-key.pem',DATA/'lan-cert.json'
 try:
  info=json.loads(meta.read_text())
  if cert_path.exists() and key_path.exists() and info.get('ca') and set(ips)<=set(info['ips']):return str(cert_path),str(key_path)
 except (OSError,ValueError,KeyError):pass
 x509,NameOID,EKU,hashes,serialization,ec=_crypto()
 ca_cert,ca_key=ensure_ca()
 key=ec.generate_private_key(ec.SECP256R1());now=datetime.datetime.now(datetime.timezone.utc)
 alt=[x509.DNSName('localhost'),x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]+[x509.IPAddress(ipaddress.ip_address(ip)) for ip in ips]
 cert=(x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'DraftMate')])).issuer_name(ca_cert.subject)
  .public_key(key.public_key()).serial_number(x509.random_serial_number())
  .not_valid_before(now-datetime.timedelta(days=1)).not_valid_after(now+datetime.timedelta(days=397))
  .add_extension(x509.SubjectAlternativeName(alt),critical=False)
  .add_extension(x509.BasicConstraints(ca=False,path_length=None),critical=True)
  .add_extension(x509.ExtendedKeyUsage([EKU.SERVER_AUTH]),critical=False)
  .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),critical=False)
  .sign(ca_key,hashes.SHA256()))
 _write_key(key_path,key)
 # Send the CA with the server certificate so devices can build the chain.
 cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM)+ca_cert.public_bytes(serialization.Encoding.PEM))
 meta.write_text(json.dumps({'ips':ips,'ca':True}))
 return str(cert_path),str(key_path)

def ca_der():
 x509,_,_,_,serialization,_=_crypto()
 return x509.load_pem_x509_certificate(CA_CERT.read_bytes()).public_bytes(serialization.Encoding.DER)
