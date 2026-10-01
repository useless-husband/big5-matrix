//! Records the resolved encoding_rs version (from Cargo.lock) and the compiler version, so the
//! adapter can report exactly what was tested.

use std::process::Command;

fn main() {
    let lock = std::fs::read_to_string("Cargo.lock").expect("Cargo.lock");
    let mut version = "unknown".to_string();
    let mut in_pkg = false;
    for line in lock.lines() {
        if line == "name = \"encoding_rs\"" {
            in_pkg = true;
        } else if in_pkg && line.starts_with("version = ") {
            version = line
                .trim_start_matches("version = ")
                .trim_matches('"')
                .to_string();
            break;
        }
    }
    println!("cargo:rustc-env=ENCODING_RS_VERSION={}", version);
    let rustc = std::env::var("RUSTC").unwrap_or_else(|_| "rustc".into());
    let out = Command::new(rustc)
        .arg("--version")
        .output()
        .expect("rustc --version");
    let v = String::from_utf8_lossy(&out.stdout);
    let v = v.split_whitespace().nth(1).unwrap_or("unknown");
    println!("cargo:rustc-env=RUSTC_VERSION={}", v);
    println!("cargo:rerun-if-changed=Cargo.lock");
}
