import serial
import time

def initialize_bill_acceptor(port="/dev/ttyUSB0", baudrate=9600):
    """Initialize RS232 connection with the bill acceptor."""
    for attempt in range(3):  # Retry logic
        try:
            ser = serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_EVEN,
                stopbits=serial.STOPBITS_ONE,
                timeout=1
            )
            print(f"Connected to bill acceptor on {port} with baudrate {baudrate}.")
            return ser
        except serial.SerialException as e:
            print(f"Attempt {attempt + 1}: Error initializing serial port: {e}")
            time.sleep(2)
    print("Failed to initialize serial connection after 3 attempts.")
    return None

def send_command(ser, command):
    """Send a command to the bill acceptor."""
    try:
        ser.write(command)
        print(f"Command sent: {command.hex()}")
    except serial.SerialException as e:
        print(f"Error sending command: {e}")

def receive_response(ser):
    """Receive response from the bill acceptor."""
    try:
        if ser.in_waiting > 0:
            response = ser.read(ser.in_waiting)
            print(f"Received response: {response.hex()}")
            return response
    except serial.SerialException as e:
        print(f"Error receiving response: {e}")
    return None

def handle_error_response(ser, response):
    """Handle error responses and send appropriate recovery commands."""
    error_codes = {
        b'\x20': "Motor Failure",
        b'\x21': "Checksum Error",
        b'\x22': "Bill Jam",
        b'\x23': "Bill Removed",
        b'\x24': "Stacker Open",
        b'\x25': "Sensor Problem",
        b'\x27': "Bill Fish",
        b'\x28': "Stacker Problem",
        b'\x29': "Bill Reject",
        b'\x2A': "Invalid Command",
    }
    error_message = error_codes.get(response[:1], "Unknown Error")
    print(f"Error detected: {error_message}")

    if response[:1] in [b'\x20', b'\x22', b'\x28']:  # Motor Failure, Bill Jam, or Stacker Problem
        print("Attempting to reset due to hardware issue...")
        send_command(ser, b'\x30')  # Reset command
    else:
        print("No specific recovery action defined for this error.")

    # Re-enable bill acceptor after resolving issue
    send_command(ser, b'\x3E')  # Enable command

def process_response(ser, response):
    """Process the response received from the bill acceptor."""
    # Ignore standalone `00`
    if response == b'\x00':
        print("Received idle status (00), no action needed.")
        return

    # Remove leading `00` if present
    if response.startswith(b'\x00'):
        print("Detected leading 00 byte, removing it.")
        response = response[1:]  # Strip the leading byte

    if response:
        if response == b'\x80\x8F':  # Power-up acknowledgment request
            print("Power-up acknowledgment request received.")
            send_command(ser, b'\x02')  # Send acknowledgment
        elif response.startswith(b'\x81'):  # Escrow signal
            print(f"Bill validation message received: {response.hex()}")
            bill_type = response[2]
            value = get_value_from_bill_type(bill_type)
            print(f"Bill type: {bill_type}, Value: {value}")
            send_command(ser, b'\x02')  # Accept the bill
        elif response[:1] in [b'\x20', b'\x21', b'\x22', b'\x28']:  # Error codes
            handle_error_response(ser, response)
        else:
            print(f"Unknown response: {response.hex()}")
    else:
        print("Received empty or invalid response.")

def check_status(ser):
    """Send polling command to check the status of the bill acceptor."""
    try:
        send_command(ser, b'\x0C')  # Polling command
        response = receive_response(ser)
        if response:
            process_response(ser, response)
    except Exception as e:
        print(f"Error while checking status: {e}")

def get_value_from_bill_type(bill_type):
    """Map bill type to value."""
    value_map = {
        64: "10 nghìn",
        65: "20 nghìn",
        66: "50 nghìn",
        67: "100 nghìn",
        68: "200 nghìn",
        69: "500 nghìn"
    }
    return value_map.get(bill_type, "Unknown")

def main():
    ser = initialize_bill_acceptor(port="/dev/ttyUSB0")
    if not ser:
        return

    try:
        while True:
            check_status(ser)
            time.sleep(0.2)  # Polling interval
    except KeyboardInterrupt:
        print("Exiting program.")
    finally:
        if ser and ser.is_open:
            ser.close()
            print("Serial port closed.")

if __name__ == "__main__":
    main()

