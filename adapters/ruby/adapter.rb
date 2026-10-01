# frozen_string_literal: false
# Adapter for the transcoders built into Ruby. See big5matrix/protocol.py.
# Codecs: Big5, CP950, CP951, Big5-HKSCS (alias Big5-HKSCS:2008), Big5-UAO.

if ARGV.length != 1
  warn 'usage: adapter.rb --version | adapter.rb <encoding>'
  exit 2
end
if ARGV[0] == '--version'
  puts "version=Ruby #{RUBY_VERSION}p#{RUBY_PATCHLEVEL} (#{RUBY_PLATFORM})"
  puts "key=#{RUBY_VERSION}"
  exit 0
end

enc = Encoding.find(ARGV[0])
out = +''
$stdin.each_line do |line|
  op, arg = line.chomp.split("\t")
  res =
    case op
    when 'd'
      s = [arg].pack('H*').force_encoding(enc)
      t = s.encode(Encoding::UTF_8, invalid: :replace, undef: :replace, replace: "�")
      t.empty? ? '-' : t.codepoints.map { |c| format('%04X', c) }.join(' ')
    when 'e'
      s = arg.split(' ').map { |c| c.to_i(16) }.pack('U*')
      begin
        b = s.encode(enc)
        b.empty? ? '-' : b.unpack1('H*').upcase
      rescue Encoding::UndefinedConversionError, Encoding::InvalidByteSequenceError,
             Encoding::ConverterNotFoundError
        '!'
      end
    else
      raise "bad op #{op}"
    end
  out << "#{op}\t#{arg}\t#{res}\n"
  if out.bytesize > 65_536
    $stdout.write(out)
    out = +''
  end
end
$stdout.write(out)
