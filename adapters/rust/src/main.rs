//! Adapter for the encoding_rs crate (Firefox's encoding library). See big5matrix/protocol.py.

use std::io::{self, BufRead, BufWriter, Write};

use encoding_rs::{BIG5, EncoderResult};

fn code_points(s: &str) -> String {
    if s.is_empty() {
        return "-".to_string();
    }
    s.chars()
        .map(|c| format!("{:04X}", c as u32))
        .collect::<Vec<_>>()
        .join(" ")
}

fn parse_hex_bytes(s: &str) -> Vec<u8> {
    (0..s.len() / 2)
        .map(|i| u8::from_str_radix(&s[2 * i..2 * i + 2], 16).expect("hex byte"))
        .collect()
}

fn parse_code_points(s: &str) -> String {
    s.split_whitespace()
        .map(|f| char::from_u32(u32::from_str_radix(f, 16).expect("hex")).expect("scalar"))
        .collect()
}

/// Encodes without the HTML numeric character reference fallback, so an unmappable
/// character is reported instead of being replaced.
fn encode_strict(s: &str) -> Option<Vec<u8>> {
    let mut encoder = BIG5.new_encoder();
    let cap = encoder
        .max_buffer_length_from_utf8_without_replacement(s.len())
        .expect("buffer length");
    let mut out = vec![0u8; cap];
    let (result, read, written) = encoder.encode_from_utf8_without_replacement(s, &mut out, true);
    match result {
        EncoderResult::InputEmpty => {
            assert_eq!(read, s.len());
            out.truncate(written);
            Some(out)
        }
        EncoderResult::Unmappable(_) => None,
        EncoderResult::OutputFull => panic!("output buffer too small"),
    }
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 2 {
        eprintln!("usage: adapter --version | adapter big5");
        std::process::exit(2);
    }
    if args[1] == "--version" {
        println!(
            "version=encoding_rs {} (rustc {})",
            env!("ENCODING_RS_VERSION"),
            env!("RUSTC_VERSION")
        );
        println!("key={}", env!("ENCODING_RS_VERSION"));
        return;
    }
    if args[1] != "big5" {
        eprintln!("unknown codec {}", args[1]);
        std::process::exit(2);
    }
    let stdin = io::stdin();
    let mut out = BufWriter::new(io::stdout().lock());
    for line in stdin.lock().lines() {
        let line = line.expect("read");
        let (op, arg) = line.split_once('\t').expect("tab");
        let res = match op {
            "d" => {
                let bytes = parse_hex_bytes(arg);
                // decode_without_bom_handling: replacement mode, no BOM sniffing.
                let (text, _had_errors) = BIG5.decode_without_bom_handling(&bytes);
                code_points(&text)
            }
            "e" => match encode_strict(&parse_code_points(arg)) {
                Some(b) if b.is_empty() => "-".to_string(),
                Some(b) => b.iter().map(|x| format!("{:02X}", x)).collect(),
                None => "!".to_string(),
            },
            _ => panic!("bad op {}", op),
        };
        writeln!(out, "{}\t{}\t{}", op, arg, res).expect("write");
    }
}
