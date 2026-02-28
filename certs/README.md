Using tailscale for this project. The intention is to use Tailscale as a VPN solution for field testing.

Why? Tailscale supports its own DNS solution and also supports signing SSL certificates using LetsEncrypt. This allows use of an SSL context without having to generate and install a new root certificate on any devices that access my VPN, allowing others to assist with data capture.

Process:
1. Rename the machine using the Tailscale Admin Console to something generic (I used "mini") because this will be captured and published on a public ledger (for security purposes mostly)
2. Run the command `sudo tailscale cert mini.tail1fdac7.ts.net` which will generate a new SSL certificate for the "mini" machine
3. Add the new generated certificate to the reverse proxy
