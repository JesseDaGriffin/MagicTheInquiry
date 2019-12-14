Programmer: Jesse Griffin
Magic the Gathering Card Web Scraper
Professor: Ben McCamish

Program Description:
    This program will scrape 'scryfall.com' for the sets given in
    the program. To change what set to scrape for, change the
    variable "mtg_set". Currently, the program is only scraping
    10 sets at a time. You can find the set codes for more sets
    at 'https://scryfall.com/sets'. The program will request the
    Scryfall page of the set given and save the name of all the
    cards. Finally, it will use the api to save the details of
    each card to a SQL database.

Run Program:
    Must have database set up before program is ran. Data has
    been turned in with the program that should be created first.
    Database must be named 'MtgDb' or additional code must be 
    changed.

    *** User might need to change code ***
    Program will assume username is 'root', host is 'localhost'.
    If this is not the case for you, code must be changed.
    The password will be asked of user at runtime.

    To run the program, use command:
    > python3 magicscraperSQL.py
    This will run the program and begin saving tuples in SQL db



