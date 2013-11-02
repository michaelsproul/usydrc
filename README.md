USYD Exam Results Checker
=========================================

The usyd website for checking results is cumbersome and slow. This script checks the uni website for new results, and emails you when they finally come out.

For now only Gmail accounts are supported. If you have a burning desire to use another email provider, send me a message at micsproul (at) gmail.com

## Dependencies ##

* [Python v2](http://www.python.org/getit/)
* [Beautiful Soup 4](http://www.crummy.com/software/BeautifulSoup/bs4/doc/) and [Requests](http://docs.python-requests.org/en/latest/) (included)
* Cron (optional, Linux and OS X only)

Mac & Linux users should have Python installed already, Windows users will have to [download it](http://python.org/ftp/python/2.7.5/python-2.7.5.msi). If you already have Beautiful Soup and Requests installed system-wide you can delete the `bs4` and `requests` folders that come bundled with usydrc.

## Installation ##

Download the latest release from [here](https://github.com/gnusouth/usydrc/releases). You want the `usydrc.zip` file.

USYDRC needs to store your passwords so it can access the uni websites on your behalf, so extract this zip somewhere safe. Your home directory or My Documents folder is recommended.

## Usage ##

Windows users can double click `usydrc.py` to get started. Linux & OS X users will have to run `./usydrc.py` from the command-line.

The first time you run the script it requests your various login details and stores them in `details.txt` for future reference. The details file can also be created manually with the following format:

```
Uni: uni-key password
Gmail: username password
```

Once you have a `details.txt` file usydrc can check the uni website without you having to do anything. It's important that you always run usydrc from the folder where it's installed, so that it can access your `details.txt`.

## Running Automatically (Linux/Mac) ##

If you have `cron` installed, you can schedule the script to run regularly. I recommend every hour or so. This works great on a Raspberry Pi.

Run `crontab -e` to add a new rule. Something like:

``0 * * * * cd /home/michael/Programming/usydrc && ./usydrc.py``

If you're not a vim-guru you may want to run `export EDITOR=nano` before you edit your crontab. To check that the entry has been added correctly, run `crontab -l`.

I haven't test this (or indeed anything) on Mac, so you may want to check out `launchd` instead.

## Running Automatically (Windows) ##

To run the script automatically on Windows you can create a task using "Task Scheduler". Make sure you set the "Start in" option to the folder where you installed `usydrc.py`.

## Security ##

Unfortunately, usydrc requires access to your unencrypted passwords in order to access the Sydney Uni website. It keeps them in a file called `details.txt` in the same folder that it runs from. It is recommended that you keep this folder very safe, particularly if you use these passwords for other things. Having a password to login to your computer is highly recommended. If you feel uncomfortable about the security of usydrc, feel free to boycott it. I take no responsibility for your use (or misuse) of this software (sorry it has to be this way, but hey, it ain't all bad).

This limitation also prevented me from making usydrc into a nice shiny website.

## Bugs & Errors ##

I'm fairly sure all my code is bug-free. If you get an error it's likely because something isn't set up correctly, or the SSA website is stuffing up (it does this from time to time). If you need help or you've found a bug, just email me: micsproul (at) gmail.com

If you're using a Mac and manage to get it to work, please let me know what you did (I don't have access to any Macs).
