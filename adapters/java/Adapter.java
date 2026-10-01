// Adapter for the JDK's java.nio.charset converters. See big5matrix/protocol.py.
// Run as a single-file program: java adapters/java/Adapter.java <charset>
import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.nio.ByteBuffer;
import java.nio.CharBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.Charset;
import java.nio.charset.CharsetDecoder;
import java.nio.charset.CharsetEncoder;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.util.HexFormat;

public class Adapter {
    public static void main(String[] args) throws Exception {
        if (args.length != 1) {
            System.err.println("usage: Adapter --version | Adapter <charset>");
            System.exit(2);
        }
        if (args[0].equals("--version")) {
            System.out.println("version=" + System.getProperty("java.vm.name") + " "
                    + System.getProperty("java.runtime.version") + " ("
                    + System.getProperty("java.vendor") + ")");
            System.out.println("key=" + System.getProperty("java.version"));
            return;
        }
        Charset cs = Charset.forName(args[0]);
        // The same configuration as new String(bytes, charset): replace malformed and
        // unmappable input with the decoder's replacement, which is U+FFFD.
        CharsetDecoder dec = cs.newDecoder()
                .onMalformedInput(CodingErrorAction.REPLACE)
                .onUnmappableCharacter(CodingErrorAction.REPLACE);
        // Strict encoding: report what cannot be encoded instead of writing '?'.
        CharsetEncoder enc = cs.newEncoder()
                .onMalformedInput(CodingErrorAction.REPORT)
                .onUnmappableCharacter(CodingErrorAction.REPORT);
        HexFormat hex = HexFormat.of().withUpperCase();
        BufferedReader in = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8));
        BufferedWriter out = new BufferedWriter(new OutputStreamWriter(System.out, StandardCharsets.UTF_8), 1 << 16);
        String line;
        while ((line = in.readLine()) != null) {
            int tab = line.indexOf('\t');
            String op = line.substring(0, tab);
            String arg = line.substring(tab + 1);
            String res;
            if (op.equals("d")) {
                // decode() resets the decoder, decodes, and flushes it.
                CharBuffer cb = dec.decode(ByteBuffer.wrap(hex.parseHex(arg)));
                res = codePoints(cb.toString());
            } else if (op.equals("e")) {
                StringBuilder sb = new StringBuilder();
                for (String f : arg.split(" ")) {
                    sb.appendCodePoint(Integer.parseInt(f, 16));
                }
                try {
                    ByteBuffer bb = enc.encode(CharBuffer.wrap(sb));
                    byte[] b = new byte[bb.remaining()];
                    bb.get(b);
                    res = b.length == 0 ? "-" : hex.formatHex(b);
                } catch (CharacterCodingException e) {
                    res = "!";
                }
            } else {
                throw new IllegalArgumentException("bad op " + op);
            }
            out.write(op + "\t" + arg + "\t" + res + "\n");
        }
        out.flush();
    }

    static String codePoints(String s) {
        if (s.isEmpty()) {
            return "-";
        }
        StringBuilder sb = new StringBuilder();
        s.codePoints().forEach(cp -> {
            if (sb.length() > 0) {
                sb.append(' ');
            }
            sb.append(String.format("%04X", cp));
        });
        return sb.toString();
    }
}
