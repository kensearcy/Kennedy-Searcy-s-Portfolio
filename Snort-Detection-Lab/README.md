# Snort Network Detection Lab

## Overview
This project involved configuring Snort to monitor network traffic,
generate alerts, and apply custom detection rules in a lab environment.

## Skills Demonstrated
- Snort IDS/IPS
- Network traffic monitoring
- Custom Snort rule creation
- TCP/IP and port-based detection
- Linux command line
- Security alert analysis
- Snort configuration

## What I Did
- Configured Snort for network traffic monitoring.
- Modified the Snort configuration to enable and load local rules.
- Ran Snort in detection mode to monitor network activity.
- Created and tested a custom Snort rule for TCP traffic on port 443.
- Generated network activity to test the configured detection rule.
- Reviewed Snort alerts to verify that the rule triggered as expected.

## Example Rule
The lab included creation of a custom rule similar to:

`alert tcp any any -> any 443 (msg:"Blocking HTTPS traffic to google.com"; sid:1000001; rev:1;)`

## Full Report
The complete lab report, configuration steps, commands, results,
and screenshots are included in this folder.
