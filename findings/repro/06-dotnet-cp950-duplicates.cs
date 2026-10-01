// .NET (System.Text.Encoding.CodePages): code page 950 rejects ten byte sequences that
// Microsoft's CP950.TXT and bestfit950.txt map. Run in a console project:
//   dotnet new console -o r && cp 06-dotnet-cp950-duplicates.cs r/Program.cs && dotnet run --project r
using System.Text;

Encoding.RegisterProvider(CodePagesEncodingProvider.Instance);
var cp950 = Encoding.GetEncoding(950, EncoderFallback.ExceptionFallback, DecoderFallback.ExceptionFallback);
string[] codes = { "A2A4", "A2A5", "A2A6", "A2A7", "A2CC", "A2CE", "F9FA", "F9FB", "F9FC", "F9FD", "F9F9", "A451" };
foreach (var hex in codes)
{
    try
    {
        var s = cp950.GetString(Convert.FromHexString(hex));
        Console.WriteLine($"{hex} -> U+{(int)s[0]:X4}");
    }
    catch (DecoderFallbackException)
    {
        Console.WriteLine($"{hex} -> error");
    }
}
// CP950.TXT: A2A4 U+2550, A2A5 U+255E, A2A6 U+256A, A2A7 U+2561, A2CC U+5341, A2CE U+5345,
// F9FA U+256D, F9FB U+256E, F9FC U+2570, F9FD U+256F (each also has a second code).
