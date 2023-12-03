import os
import imaplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
import chardet
import json
import re
import logging

# Load email credentials and server information from environment variables
email_address = os.environ.get("EMAIL_ADDRESS")
password = os.environ.get("PASSWORD")
imap_server = os.environ.get("IMAP_SERVER")
imap_port = 143
mailbox = "INBOX"

# Function to convert non-serializable types to serializable types
def convert_to_serializable(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    return obj

def decode_email_header(header_value):
    if header_value:
        decoded_header, encoding = decode_header(header_value)[0]
        return decode_text(decoded_header, encoding)
    else:
        return None

# Function to decode subject and sender
def decode_text(text, encoding):
    if isinstance(text, bytes):
        try:
            result = text.decode(encoding or "utf-8", errors="replace")
        except LookupError:
            # If the encoding is not recognized, use chardet to detect it
            result = text.decode(chardet.detect(text)["encoding"] or "utf-8", errors="replace")
    else:
        result = text
    return result

def extract_email_from_from_field(from_field):
    match = re.search(r'<([^>]+)>', from_field)
    if match:
        return match.group(1)
    else:
        return None

# Function to extract email body content
def extract_email_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                return part.get_payload(decode=True).decode("utf-8", errors="replace")
    else:
        return msg.get_payload(decode=True).decode("utf-8", errors="replace")

# Function to save email data to JSON file
def save_to_json(email_data, file_name="emails.json"):
    with open(file_name, "w", encoding="utf-8") as json_file:
        json.dump(email_data, json_file, default=convert_to_serializable, ensure_ascii=False, indent=4)

try:
  # Connect to the IMAP server
  #mail = imaplib.IMAP4_SSL(imap_server, imap_port)
  mail = imaplib.IMAP4(imap_server, imap_port)
  mail.starttls()


  # Log in to your account
  mail.login(email_address, password)

  # Select the mailbox
  mail.select(mailbox)

  # Search for unread emails
  status, messages = mail.search(None, "(UNSEEN)")
  if status == "OK":
      # Get the list of email IDs
      email_ids = messages[0].split()

      email_data_list = []  # List to store email data

      for email_id in email_ids:
          # Fetch the email by ID
          status, msg_data = mail.fetch(email_id, "(RFC822)")
          if status == "OK":
              # Parse the raw email data
              raw_email = msg_data[0][1]
              msg = email.message_from_bytes(raw_email)

              delivered_to, encoding = decode_header(msg.get("Delivered-To"))[0]
              delivered_to = decode_text(delivered_to, encoding)
              sender_email = extract_email_from_from_field(delivered_to)

              # Get the sender
              from_, encoding = decode_header(msg.get("From"))[0]
              from_ = decode_text(from_, encoding)
              sender_email = extract_email_from_from_field(from_)

              # Get the Return-Path
              path_, encoding = decode_header(msg.get("Return-Path"))[0]
              path_ = decode_text(path_, encoding)
              sender_email = extract_email_from_from_field(path_)

              # Get the recipient
              to_, encoding = decode_header(msg.get("To"))[0]
              to_ = decode_text(to_, encoding)
              recipient_email = extract_email_from_from_field(to_)

              # Get the subject
              subject, encoding = decode_header(msg["Subject"])[0]
              subject = decode_text(subject, encoding)

              # Get the date
              date = parsedate_to_datetime(msg["Date"])

              # Get the email content
              content = extract_email_body(msg)

              # Get the sender
              sender_header = msg.get("Sender")
    
              # Get the date
              date = parsedate_to_datetime(msg["Date"])

              # Get the email content
              content = ""
              if msg.is_multipart():
                  for part in msg.walk():
                      if part.get_content_type() == "text/plain":
                          content = part.get_payload(decode=True).decode("utf-8", errors="replace")
                          break
              else:
                  content = msg.get_payload(decode=True).decode("utf-8", errors="replace")

              # Store email data in a dictionary
              email_data = {
                  "Date": date.isoformat(),
                  "Delivered-To":delivered_to,
                  "From": from_,
                  "Return-Path": path_,
                  "Subject": subject,
                  "Body-Content": content,
              }

              # Add the email data to the list
              email_data_list.append(email_data)
              print(email_data)

      # Save the email data to a JSON file
      save_to_json(email_data_list)

  # Logout and close the connection
  mail.logout()
except Exception as e:
    logging.error("An error occurred: %s", str(e))
