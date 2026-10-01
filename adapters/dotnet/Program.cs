// Adapter for .NET code page encodings (System.Text.Encoding.CodePages). See big5matrix/protocol.py.
//
// Codecs: "<codepage>" (strict: exception fallback for encoding, U+FFFD for decoding) and
// "<codepage>/default" (the fallbacks Encoding.GetEncoding(codepage) comes with, which on
// encoding include Windows "best fit" mappings; the bytes are reported as produced).
using System.Runtime.InteropServices;
using System.Text;

Encoding.RegisterProvider(CodePagesEncodingProvider.Instance);

if (args.Length != 1)
{
    Console.Error.WriteLine("usage: adapter --version | adapter <codepage>[/default]");
    return 2;
}
if (args[0] == "--version")
{
    var asm = typeof(CodePagesEncodingProvider).Assembly.GetName();
    Console.WriteLine($"version={RuntimeInformation.FrameworkDescription} ({asm.Name} {asm.Version})");
    Console.WriteLine($"key={Environment.Version}");
    return 0;
}

var parts = args[0].Split('/');
int codepage = int.Parse(parts[0]);
bool defaults = parts.Length > 1 && parts[1] == "default";
Encoding enc = defaults
    ? Encoding.GetEncoding(codepage)
    : Encoding.GetEncoding(codepage, EncoderFallback.ExceptionFallback, new DecoderReplacementFallback("�"));

using var stdin = new StreamReader(Console.OpenStandardInput(), new UTF8Encoding(false));
using var stdout = new StreamWriter(Console.OpenStandardOutput(), new UTF8Encoding(false), 1 << 16);
string? line;
while ((line = stdin.ReadLine()) != null)
{
    int tab = line.IndexOf('\t');
    string op = line[..tab], arg = line[(tab + 1)..];
    string res;
    if (op == "d")
    {
        // GetString uses a fresh decoder and flushes it at the end of the input.
        string s = enc.GetString(Convert.FromHexString(arg));
        res = CodePoints(s);
    }
    else if (op == "e")
    {
        var sb = new StringBuilder();
        foreach (var f in arg.Split(' '))
        {
            sb.Append(char.ConvertFromUtf32(Convert.ToInt32(f, 16)));
        }
        try
        {
            byte[] b = enc.GetBytes(sb.ToString());
            res = b.Length == 0 ? "-" : Convert.ToHexString(b);
        }
        catch (EncoderFallbackException)
        {
            res = "!";
        }
    }
    else
    {
        throw new ArgumentException($"bad op {op}");
    }
    stdout.Write($"{op}\t{arg}\t{res}\n");
}
return 0;

static string CodePoints(string s)
{
    if (s.Length == 0) return "-";
    var parts = new List<string>();
    for (int i = 0; i < s.Length; i += char.IsSurrogatePair(s, i) ? 2 : 1)
    {
        parts.Add(char.ConvertToUtf32(s, i).ToString("X4"));
    }
    return string.Join(' ', parts);
}
