// SYNTHETIC fixture: limited-scope Java detector test
package demo.ledger;

import java.security.KeyPairGenerator;
import java.security.MessageDigest;
import java.security.Signature;
import javax.crypto.*;

public class LedgerCrypto {
    private static final String WRAP = "RSA/ECB/OAEPWithSHA-256AndMGF1Padding";

    void run() throws Exception {
        KeyPairGenerator kpg = KeyPairGenerator.getInstance("EC");
        Signature s = Signature.getInstance("SHA256withECDSA");
        Cipher wrap = Cipher.getInstance(WRAP);
        Cipher legacy = Cipher.getInstance("DESede/CBC/PKCS5Padding");
        KeyAgreement ka = KeyAgreement.getInstance("ECDH");
        MessageDigest md = MessageDigest.getInstance("MD5");
        // Cipher.getInstance("RC4");   HN comment
        String note = "Cipher.getInstance(\"DES\")";  // HN string literal
        MessageDigest ok = MessageDigest.getInstance("SHA-256"); // HN modern hash
        javax.net.ssl.SSLContext ctx = javax.net.ssl.SSLContext.getInstance("TLSv1.1");
        KeyStore ks = KeyStore.getInstance("JKS"); // HN: KeyStore not imported (java.security.KeyStore missing)
    }
}
