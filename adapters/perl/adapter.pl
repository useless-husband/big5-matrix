#!/usr/bin/perl
# Adapter for Perl's Encode module (Encode::TW: big5-eten, cp950, big5-hkscs).
# See big5matrix/protocol.py.
use strict;
use warnings;
use Encode ();

if (@ARGV != 1) {
    print STDERR "usage: adapter.pl --version | adapter.pl <encoding>\n";
    exit 2;
}
if ($ARGV[0] eq '--version') {
    require Encode::TW;
    printf "version=Perl %vd, Encode %s, Encode::TW %s\n", $^V, $Encode::VERSION, $Encode::TW::VERSION;
    print "key=Encode-$Encode::VERSION\n";
    exit 0;
}
my $codec = $ARGV[0];
Encode::find_encoding($codec) or die "unknown encoding $codec\n";

binmode STDIN;
binmode STDOUT;
my $buf = '';
while (my $line = <STDIN>) {
    chomp $line;
    my ($op, $arg) = split /\t/, $line;
    my $res;
    if ($op eq 'd') {
        my $bytes = pack 'H*', $arg;
        # FB_DEFAULT: malformed input becomes U+FFFD.
        my $text = Encode::decode($codec, $bytes, Encode::FB_DEFAULT);
        $res = length($text) ? join(' ', map { sprintf '%04X', ord } split //, $text) : '-';
    } elsif ($op eq 'e') {
        my $text = join '', map { chr hex } split / /, $arg;
        my $bytes = eval { Encode::encode($codec, $text, Encode::FB_CROAK) };
        if (!defined $bytes) {
            $res = '!';
        } else {
            $res = length($bytes) ? uc unpack('H*', $bytes) : '-';
        }
    } else {
        die "bad op $op\n";
    }
    $buf .= "$op\t$arg\t$res\n";
    if (length($buf) > 65536) {
        print $buf;
        $buf = '';
    }
}
print $buf;
