import java.util.HashMap;
import java.util.Map;

/** Tiny JSON helper (no external libraries): builds strings and reads a flat {"key": value} object. */
public final class Json {
    private Json() {}

    public static String quote(String s) {
        StringBuilder sb = new StringBuilder("\"");
        for (char c : s.toCharArray()) {
            switch (c) {
                case '"': sb.append("\\\""); break;
                case '\\': sb.append("\\\\"); break;
                case '\n': sb.append("\\n"); break;
                case '\r': sb.append("\\r"); break;
                case '\t': sb.append("\\t"); break;
                default:
                    if (c < 0x20) sb.append(String.format("\\u%04x", (int) c));
                    else sb.append(c);
            }
        }
        return sb.append('"').toString();
    }

    /** Parses a flat JSON object; every value is returned as a string. */
    public static Map<String, String> parseObject(String s) {
        Map<String, String> map = new HashMap<>();
        int i = s.indexOf('{');
        if (i < 0) throw new IllegalArgumentException("Invalid request data.");
        i++;
        while (i < s.length()) {
            i = skipWs(s, i);
            if (i >= s.length() || s.charAt(i) == '}') break;
            if (s.charAt(i) == ',') { i++; continue; }
            if (s.charAt(i) != '"') throw new IllegalArgumentException("Invalid request data.");
            int[] pos = {i};
            String key = readString(s, pos);
            i = skipWs(s, pos[0]);
            if (i >= s.length() || s.charAt(i) != ':') throw new IllegalArgumentException("Invalid request data.");
            i = skipWs(s, i + 1);
            String val;
            if (i < s.length() && s.charAt(i) == '"') {
                pos[0] = i;
                val = readString(s, pos);
                i = pos[0];
            } else {
                int st = i;
                while (i < s.length() && ",}".indexOf(s.charAt(i)) < 0) i++;
                val = s.substring(st, i).trim();
            }
            map.put(key, val);
        }
        return map;
    }

    private static int skipWs(String s, int i) {
        while (i < s.length() && Character.isWhitespace(s.charAt(i))) i++;
        return i;
    }

    private static String readString(String s, int[] pos) {
        StringBuilder sb = new StringBuilder();
        int i = pos[0] + 1;
        while (i < s.length() && s.charAt(i) != '"') {
            char c = s.charAt(i);
            if (c == '\\' && i + 1 < s.length()) {
                char n = s.charAt(++i);
                switch (n) {
                    case 'n': sb.append('\n'); break;
                    case 't': sb.append('\t'); break;
                    case 'r': sb.append('\r'); break;
                    case 'u':
                        sb.append((char) Integer.parseInt(s.substring(i + 1, i + 5), 16));
                        i += 4;
                        break;
                    default: sb.append(n);
                }
            } else {
                sb.append(c);
            }
            i++;
        }
        pos[0] = i + 1;
        return sb.toString();
    }
}
