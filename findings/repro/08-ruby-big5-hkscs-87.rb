# Ruby Big5-HKSCS: the encoder writes HKSCS-2008 characters to row 0x87, which the decoder
# rejects. Observed with Ruby 2.6.10 (macOS system Ruby); re-test on a current Ruby.
s = "㓦"
b = s.encode('Big5-HKSCS')
puts "#{RUBY_VERSION}: U+34E6 -> #{b.unpack1('H*')}"
begin
  puts "back: #{b.encode('UTF-8').inspect}"
rescue => e
  puts "back: #{e.class}: #{e.message}"
end
