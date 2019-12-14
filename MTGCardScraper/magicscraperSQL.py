import os
import sys
from bs4 import BeautifulSoup
from lxml import etree
import json
import requests
import pymysql
import getpass
import time


def searchCard(card_name):
    # Create url for api
    card = card_name.replace(' ', '+').lower()
    return 'https://api.scryfall.com/cards/named?exact=' + card


def main():
    # Connect with mysql database
    # Change username and password in order to access your database
    username = "root"
    password = getpass.getpass("MySQL password: ")
    conn = pymysql.connect(host='localhost', port=3306, user=username, passwd=password, db='MtgDb')
    cur = conn.cursor()
    # Standard sets:
    # m20
    # war
    # rna
    # grn
    # Change the contents of this array to the sets you would like to scrape for
    # inv oldest set
    sets = ['pcy', 'nem', 'mmq', '6ed', 'ulg', 'usg', 'uds', 'exo', 'sth', 'tmp', '5ed']
    #['9ed', 'sok', 'bok', 'chk', '5dn', 'dst', 'mrd', '8ed', 'scg', 'lgn', 'ons', 'jud', 'tor', 'ody', 'apc', '7ed', 'pls', 'inv']
    cards_saved = 0
    for mtg_set in sets:
        # Webpage for scraping
        scryfall = "https://scryfall.com/sets/" + mtg_set
        # Request html for webpage
        time.sleep(.1)
        sf_html = requests.get(scryfall)

        # Parse html
        soup = BeautifulSoup(sf_html.text, 'html.parser')

        # Search for names of cards on website
        cards = soup.find_all('span', {'class': 'card-grid-item-invisible-label'})

        for card in cards:
            skip = False
            # Use Scryfall api to retrieve info about each card
            searched_card = searchCard(card.get_text())
            time.sleep(.1)
            card_response = requests.get(searched_card)
            if card_response:
                # Format response to json
                card = card_response.json()

                # This if statement filters out japanese cards from war of the spark
                if 'id' in card:
                    card_colors = ""
                    # Check if card has a color and add it to its colors
                    if 'colors' in card:
                        for color in card['colors']:
                            card_colors += color

                    # If card is a creature, take save power and toughness
                    if 'power' in card:
                        power = card['power']
                    else:
                        power = None
                    if 'toughness' in card:
                        toughness = card['toughness']
                    else:
                        toughness = None

                    # If card isn't "vanilla", save abilities and card text
                    if "oracle_text" in card:
                        oracle_text = card['oracle_text']
                    else:
                        oracle_text = None

                    # If it doesn't have a mana_cost
                    if "mana_cost" in card:
                        mana_cost = card['mana_cost']
                    else:
                        mana_cost = None

                    # If it doesn't have a mana_cost
                    if "image_uris" in card:
                        image_uris = card['image_uris']['normal']
                    else:
                        skip = True

                    # Store card values to be saved to sql db
                    values = (card['id'], card['name'], card['set'], card['set_name'], card['rarity'], card_colors, card['cmc'], mana_cost, card['type_line'], power, toughness, oracle_text, image_uris)

                    # print(values)
                    # Add new card to db or print error and card name
                    if not skip:
                        try:
                            cur.execute("""INSERT INTO MtgCards (id, name, setid, set_name, rarity, colors, cmc, mana_cost, type, power, toughness, text, img) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""", values)
                            cards_saved += 1
                            print("New Card", cards_saved)
                        except Exception as e:
                            # Show the error with insertion as well as the cards name
                            print(e)
                            print(card['name'])

        conn.commit()
        print("Cards saved so far: ", cards_saved)

    cur.close()
    conn.close()


if __name__ == '__main__':
    main()
