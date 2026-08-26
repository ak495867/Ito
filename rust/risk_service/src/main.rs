use ito_risk_service::{evaluate, hardware::{self, HardwarePipeline}, RiskRequest};
use std::env;
use std::io::{self, BufRead, BufReader, Read, Write};
use std::net::{TcpListener, TcpStream};

fn respond(request: &str) -> String {
    match serde_json::from_str::<RiskRequest>(request) {
        Ok(value) => serde_json::to_string(&evaluate(value)).unwrap_or_else(|_| "{\"error\":\"serialization_failure\"}".to_owned()),
        Err(_) => "{\"error\":\"request_invalid\"}".to_owned(),
    }
}

fn serve_stream(stream: TcpStream) -> io::Result<()> {
    let writer = stream.try_clone()?;
    let mut output = io::BufWriter::new(writer);
    let reader = BufReader::new(stream);
    for line in reader.lines() {
        let value = line?;
        writeln!(output, "{}", respond(&value))?;
        output.flush()?;
    }
    Ok(())
}

fn main() -> io::Result<()> {
    if env::args().any(|argument| argument == "--emit-frame") {
        let mut input = String::new();
        io::stdin().read_to_string(&mut input)?;
        let request = serde_json::from_str::<RiskRequest>(input.trim()).map_err(|_| io::Error::new(io::ErrorKind::InvalidInput, "request_invalid"))?;
        let pipeline = HardwarePipeline::new();
        let (frame, response) = pipeline.prepare(request);
        println!("{}", serde_json::json!({"frame_hex": hardware::to_hex(&frame), "response": response}));
        return Ok(());
    }
    if env::args().any(|argument| argument == "--once") {
        let mut input = String::new();
        io::stdin().read_line(&mut input)?;
        println!("{}", respond(input.trim()));
        return Ok(());
    }
    let listener = TcpListener::bind("127.0.0.1:9110")?;
    for stream in listener.incoming() {
        if let Ok(value) = stream {
            let _ = serve_stream(value);
        }
    }
    Ok(())
}
