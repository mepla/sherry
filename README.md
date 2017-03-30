# Sherry
TP-Link Modem bandwidth monitoring

## Description
Sherry is a simple command line tool to monitor bandwidth usage of each device connected to a TP-Link modem.

- This was tested and fully functional on `TP-Link Archer D20` 
- It will probably work for any TP-Link modem or wireless router that uses the new web interface (I haven't tested it though).


## Getting started
This is a script I put together in a day as soon as I bought an Archer D20 and realized that it doesn't have a decent bandwidth monitoring interface (although it has bandwidth limits!). Since this was a hasty attempt to only alleviate my need, it does not currently have a setup.py and can not be installed. You can use it as a standalone script in a couple of ways:

### Run using Python
1. Download the Sherry project files 
2. Change to its directory 
3. Run `pip install -r requirements.txt`
4. Run Sherry like any other Python script: `python main.py -h`

Of course this only shows the help message and available command line arguments (which is explained in Using Sherry section).

### Run using a bash script
This is pretty much the same as running it using Python, but it is a way to make it more usable (like it is actually installed).

1. Make a copy of `sherry.sh` bash script template and change its variables to match your environment.
2. Move the file to an executable path (e.g `/usr/local/bin/sherry`).
3. Make it executable (`sudo chmod +x /usr/local/bin/sherry`).
4. Run it as an installed script: `sherry`

## Using Sherry
As a command line script Sherry has the following arguments (which you can see using `-h` argument):

```
usage: main.py [-h] [-a IP_ADDR] [-u UNIT] [-s SLEEP_TIME] -p PASSWORD
               [--reset]

optional arguments:
  -h, --help     show this help message and exit
  -a IP_ADDR     Modem address (Optional, defaults to: 192.168.1.1)
  -u UNIT        Unit: b, B, kb, kB, mb, mB (Optional, defaults to: kB)
  -s SLEEP_TIME  Sleep time between each request in float seconds (Optional,
                 defaults to: 1, minimum: 0.5)
  -p PASSWORD    Modem password (Mandatory)
  --reset        Reset usage data (equivalent to using the reset button in
                 statistics menu of web interface)

```

The only mandatory argument is PASSWORD which is the login password you use for your modem's web interface. If you followed the above bash script running method, the script template there has password field in it, so you would'nt need to enter it every time. 

### Running mode
When Sherry is running you will see something like this:

```
+---------------+-------------------+--------------------------+------------------+--------------+
| IP            | MAC               | Name                     |   Current (kBps) |   Total (kB) |
|---------------+-------------------+--------------------------+------------------+--------------|
| 192.168.1.160 | XX:XX:XX:XX:XX:XX | DEVICE_NAME01            |            10.64 |        74570 |
| 192.168.1.100 | XX:XX:XX:XX:XX:XX | DEVICE_NAME02            |             0    |         1438 |
| 192.168.1.159 | XX:XX:XX:XX:XX:XX | DEVICE_NAME03            |             0    |       212765 |
| 192.168.1.158 | XX:XX:XX:XX:XX:XX | DEVICE_NAME04            |             0    |       188012 |
| 192.168.1.2   | XX:XX:XX:XX:XX:XX | DEVICE_NAME05            |             0    |        38403 |
| 192.168.1.161 | XX:XX:XX:XX:XX:XX | DEVICE_NAME06            |             0    |            0 |
| 192.168.2.100 | XX:XX:XX:XX:XX:XX | -                        |             0    |            0 |
| 192.168.1.153 | XX:XX:XX:XX:XX:XX | DEVICE_NAME07            |             0    |        16685 |
+---------------+-------------------+--------------------------+------------------+--------------+

(q)Quit (t,c,i)Sort Total,Current,IP (r)Reset Totals (h)Reset Hostnames (u)Change Unit: 

```

As you can see you have various control options when in running mode, press one of these keys to perform the corresponding action:


- `q` To quit (equivalent to using ctrl+c)
- `t` To sort the table by Total bytes (last column)
- `c` To sort the table by Current speed
- `i` To sort the table by IP
- `r` Reset modem's usage data (equivalent to using --reset when running the script)
- `h` Refresh hostnames (e.g: DEVICE_NAME01). Sometimes the modem return Unkown or no results for a MAC address hostname. 
- `u` Change unit (equivalent to using `-u UNIT` when running the script, possible values: b, B, kb, kB, mb, mB)


## How it works
This script uses http requests based on what TP-Link web interface does. This is done using an always running loop making requests with a specific sleep duration between each iteration (Which is configurable with command line arguments).

All data is retreived from `Web Interface > Advanced > System Tools > Statistics` and other pages of web interface.

The bandwidth usage (per second column) is calculated like this: `(Current Bytes - Last Current Bytes)/sleep_time`


## Do I suck?
Well I did this in a bit of a hurry so the code is pretty messy and there are a lot of issues that I know can be improved but there are probably a lot that I don't know. So I'd appreciate it if you have any suggestions or better ways to do things.
  
You can contact me using my email (soheil.nasirian@gmail.com) or through github. 