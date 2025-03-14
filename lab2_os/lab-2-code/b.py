import serial
import time
import sys

# Configure the serial port

ser = serial.Serial('/dev/ttyACM0', 115200, timeout=2)  # Adjust if needed
time.sleep(2)  # Wait for the connection to stabilize

# Global variables to hold the extracted version digits
a = None
b = None



POLYNOMIAL = 0x04C11DB7

def crc32(data, crc=0xFFFFFFFF):
    """Calculate CRC32 for a single byte of data."""
    crc = crc ^ data  # XOR current byte with the CRC value

    # Perform the CRC bitwise calculation
    for i in range(8):  # Loop over bits (8 bits in a byte)
        if (crc & 0x80000000) != 0:
            crc = (crc << 1) ^ POLYNOMIAL  # Apply the polynomial if the MSB is 1
        else:
            crc = crc << 1  # Shift CRC left if MSB is 0

    return crc & 0xFFFFFFFF  # Return the updated CRC

def Calculate_checksum(data, crc=0xFFFFFFFF):
    """Calculate the CRC32 for a sequence of data bytes."""
    for byte in data:
        crc = crc32(byte, crc)  # Update CRC for each byte in the data
    
    # Padding to ensure data length is a multiple of 4
    remaining_bytes = len(data) % 4
    if remaining_bytes > 0:
        for _ in range(4 - remaining_bytes):
            crc = crc32(0, crc)  # Pad with zeros to complete the chunk
    
    return crc













def calculate_checksum(data):
    checksum = 0
    for byte in data:
        checksum ^= byte
    return checksum


def extract_version_from_binary_file(file_path):
    """Reads a binary file, finds 'OS Version:' and extracts the version digits."""
    global a, b
    try:
        search_string = b'OS Version:'  # Convert the search string to bytes
        with open(file_path, 'rb') as file:
            binary_data = file.read()
        
        # Find the index of the search string
        index = binary_data.find(search_string)
        if index != -1:
            # Extract the characters following 'OS Version:'
            version_start_index = index + len(search_string)
            version_data = binary_data[version_start_index:version_start_index + 3]  # Include up to 3 characters for '52\n'
            
            # Convert to a string, remove non-digit characters, and extract the two digits
            version_string = version_data.decode(errors='ignore').strip()
            version_digits = ''.join(filter(str.isdigit, version_string))  # Filter only digits
            
            if len(version_digits) >= 2:
                a, b = int(version_digits[0]), int(version_digits[1])
                print(f"Extracted version digits: a={a}, b={b}")
            else:
                print("Version digits not found or invalid.")
        else:
            print("Search string not found in the binary file.")
    except FileNotFoundError:
        print(f"File not found: {file_path}")
    except Exception as e:
        print(f"An error occurred while reading the file: {e}")




def send_binary_file(file_path):
    # Step 1: Read the actual binary file
    with open(file_path, 'rb') as f:
        binary_data = f.read()

    file_size = len(binary_data)
    print(f"File size: {file_size} bytes")

    # Step 2: Send the file size first as a 5-character string
    ser.write(f"{file_size}".encode())  # Send file size as a 5-character string
    response = ser.readline().decode().strip()

    print(f"Ack for file size: {response}")
    
    offset = 0
    while offset < file_size:
        # Determine the chunk size: if remaining data is less than 32 bytes, send that size, otherwise send 32 bytes
        remaining_data = file_size - offset
        chunk_size = min(32, remaining_data)
        
        chunk = binary_data[offset:offset+chunk_size]
        checksum = calculate_checksum(chunk)

        ser.write(chunk)  # Send chunk
        print(f"Sent chunk of size {chunk_size}: {chunk}")
        ser.write(bytes([checksum]))  # Send checksum

        # Wait for acknowledgment from STM32
        response = ser.readline().decode().strip()
        print(f"Response: {response}")
        if response == "OK":
            offset += chunk_size
        elif response == "RESEND":
            print("Resending chunk...")
        else:
            print("Unexpected response:", response)
            break

    print("Binary file sent successfully.")

try:
    while True:
        # Read data from STM32
        incoming = ser.readline().decode('utf-8', errors='ignore').strip()

        if incoming:
            print(f"Raw incoming data: '{incoming}'")  # Debugging the exact content

            if incoming == "have u any updated version":
                user_input = input("Input y/n: ")
                sys.stdout.flush()  # Ensure the output is printed immediately
                ser.write(user_input.encode('utf-8')) 

            elif incoming == "ok,send this":
                print("Sending file...")
                sys.stdout.flush()  # Ensure the output is printed immediately
                send_binary_file('/home/as/Documents/today/duos24new.bin')  # Replace with your binary file path
            
            elif incoming == "notun":
                user_input = input("Input version in 2 digit: ")
                user_input = str(user_input)
                print(user_input)
                sys.stdout.flush()  # Ensure the output is printed immediately
                ser.write(user_input.encode('utf-8')) 
            
            elif incoming == "extract":
                extract_version_from_binary_file('/home/as/Documents/today/duos24new.bin')
                  # Replace with your source file path
            
                if a is not None and b is not None:
                    version_string = f"{a}{b}"  # Combine a and b into a 2-character string
                    print(f"Sending extracted version: {version_string}")  # Debug message
                    sys.stdout.flush()  # Ensure output is printed immediately
                    ser.write(version_string.encode('utf-8'))  # Send the version string over the serial port
                else:
                    print("Version digits not available, nothing to send.")
                    sys.stdout.flush()   
                

except KeyboardInterrupt:
    print("Exiting...")
finally:
    ser.close()
