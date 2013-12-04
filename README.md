USYD Exam Results Checker
=========================================

The usyd website for checking results is cumbersome and slow. This script checks the uni website for new results, and emails you when they finally come out.

**Testers Wanted: If you have a non-Gmail, non-university email account, please let me know if this works for you.**

## Dependencies ##

* [Python v2](http://www.python.org/getit/)
* [Beautiful Soup 4](http://www.crummy.com/software/BeautifulSoup/bs4/doc/) (included)
* [Requests](http://docs.python-requests.org/en/latest/) (included)
* [Keyring](https://pypi.python.org/pypi/keyring) (included, optional) Required for more secure password management.
* Cron (optional, Linux and OS X only)

Mac & Linux users should have Python installed already, Windows users will have to [download it](http://python.org/ftp/python/2.7.6/python-2.7.6.msi).

If you're Python savvy, run `sudo pip2 install beautifulsoup4 requests keyring`.

## Installation ##

Download the latest release from [here](https://github.com/gnusouth/usydrc/releases). You want the `usydrc.zip` file.

Extract this zip file somewhere safe; your Home or My Documents folder is recommended.

## Usage ##

Windows users can double click `usydrc.py` to get started. Linux & OS X users will have to run `./usydrc.py` from the command-line.

The first time you run the script it requests your various login details and stores them in `details.txt` for future reference. Once you have a details file, usydrc can check for new results without your intervention. It's important that you always run usydrc from the folder where it's installed, so that it can access this file, and its record of existing results.

Security Note: If everything is set up correctly, no passwords will be stored in `details.txt`.

## Running Automatically (Linux/Mac) ##

If you have `cron` installed, you can schedule the script to run regularly. I recommend every hour or so.

Run `crontab -e` to add a new rule. Something like:

``0 * * * * cd /home/michael/Programming/usydrc && ./usydrc.py``

If you're not a vim-guru you may want to run `export EDITOR=nano` before you edit your crontab. To check that the entry has been added correctly, run `crontab -l`.

I haven't test this (or indeed anything) on Mac, so you may want to check out `launchd` instead.

## Running Automatically (Windows) ##

To run the script automatically on Windows you can create a task using "Task Scheduler". Make sure you set the "Start in" option to the folder where you installed `usydrc.py`.

## Contributors

* [Michael Sproul](https://github.com/gnusouth)
* [Jacqui Leykam](https://github.com/jqln-0)
* [Denbeigh Stevens](https://github.com/denbeigh2000)
* [James Cooper-Stanbury](https://github.com/JunkyJames)

## Bugs & Errors ##

If you need help or you've found a bug, just email me: micsproul (at) gmail.com
