import pymysql
from flask import Flask, render_template, url_for, request, session
from jinja2 import Template
import whoosh
from whoosh.index import create_in
from whoosh.index import open_dir
from whoosh.fields import *
from whoosh.qparser import QueryParser
from whoosh.qparser import MultifieldParser
from whoosh import qparser
import getpass
import pickle
import pygal
from pygal.style import Style
import os
import json
from collections import OrderedDict

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0


def opendeck():
    # Open pickle file representing the deck
    try:
        pickle_in = open("deck.pickle", "rb")
        deck = pickle.load(pickle_in)
        pickle_in.close()
        print("pickle open")
    except Exception as e:
        print("except")
        deck = {}

    return deck


def ordering(dictionary):
    """Dictionary passed in will be passed to a list and then Sorted.  List is then
    converted to OrderedDict and returned"""

    orderlist = []

    for key in dictionary:
        tup = (key, dictionary.get(key))
        orderlist.append(tup)

    orderlist.sort(key=lambda tup: tup[1], reverse=True)

    orderedDictionary = OrderedDict()

    for element in orderlist:

        orderedDictionary[element[0]] = element[1]

    return orderedDictionary


def mana_graph(query, dictionary, delimit, f, title, graph_file, custom):
    """Mana graph is used to parse color entries and increment each value for mana file"""
    splitter = query.split()
    mana = splitter[-1]

    graph_data = query.split(delimit)

    for letter in graph_data[1]:
        dictionary[letter] = dictionary.get(letter) + 1

    if os.path.isfile(f):

        with open(f, 'r') as fp:
            data = json.load(fp)

        with open(f, 'w') as fp:

            for mana in data:
                data[mana] = data.get(mana) + dictionary.get(mana)
                print(mana + ": " + str(data.get(mana)))
            json.dump(data, fp)
            print("printing chart")
            mana_color_chart(data, graph_file, title, custom)

    else:
        with open(f, 'w') as fp:
            json.dump(color, fp)


def grapher(query, dictionary, f, title, graph_file):

    dictionary[query] = dictionary.get(query) + 1

    if os.path.isfile(f):

        with open(f, 'r') as fp:
            data = json.load(fp)

        with open(f, 'w') as fp:

            data[query] = data.get(query) + dictionary.get(query)
            json.dump(data, fp)
        charter(data, graph_file, title, None)

    else:
        with open(f, 'w') as fp:
            json.dump(dictionary, fp)


def card_graph(query, dictionary, f, title, graph_file):

    if os.path.isfile(f):

        with open(f, 'r') as fp:
            data = json.load(fp)

        with open(f, 'w') as fp:
            if query in data:
                data[query] = data.get(query) + 1

                orderedDictionary = ordering(data)

                json.dump(orderedDictionary, fp)
                charter(orderedDictionary, graph_file, title, 9)

            else:
                data[query] = 1
                orderedDictionary = ordering(data)
                json.dump(orderedDictionary, fp)
                charter(data, graph_file, title, 9)

    else:
        with open(f, 'w') as fp:
            json.dump(dictionary, fp)
            charter(dictionary, graph_file, title, 9)


def mana_color_chart(dictionary, f, title, custom):
    bar_chart = pygal.Bar(style=custom, print_values=True)
    bar_chart.title = title

    for key, value in dictionary.items():
        bar_chart.add(key, value)

    bar_chart.render_to_file(f)


def charter(dictionary, f, title, count):
    bar_chart = pygal.Bar(print_values=True)
    bar_chart.title = title

    if count is None:

        for key, value in dictionary.items():
            bar_chart.add(key, value)

    else:
        counter = 0
        for key, value in dictionary.items():
            bar_chart.add(key, value)
            counter = counter + 1
            if counter > count:
                break

    bar_chart.render_to_file(f)


# Route for home/search page
@app.route('/', methods=['GET', 'POST'])
def index():
    print("Someone is at the home page.")
    return render_template('searchpage.html')


# Route for graph/stats page
@app.route('/graph', methods=['GET', 'POST'])
def graph():
    print("Someone is at the graph page.")
    return render_template('graph.html')


# Route for results continued page
@app.route('/results/<page>/<query2>', methods=['GET', 'POST'])
def additional_pages(page, query2):

    # Increase page count to display next 12 cards
    page2 = int(page) + 1

    # Rerun query to get the next 12 cards
    name, cmc, img, card_type, set_name, current_page, page_count = mySearcher.search(query2, int(page2))
    print(name)

    # Gather tcgplayer shop url for each card returned
    tcgurl = "https://shop.tcgplayer.com/magic/"
    urls = {}

    # Create url for each card using the setname and name of the card
    # Parse set and name to create url in the format needed by tcgplayer
    for i in range(len(name)):
        # If a core set, slightly different url, add set code after setname
        year = set_name[i][-2] + set_name[i][-1]
        if "Magic 20" in set_name[i]:
            urls[name[i]] = tcgurl + set_name[i].replace(' ', '-').replace(',', '').replace(':', '').replace('.', '').replace(' //', '') + '-m' + year + '/' + name[i].replace(' //', '').replace(' ', '-').replace(',', '').replace(':', '').replace('.', '')
        else:
            urls[name[i]] = tcgurl + set_name[i].replace(' ', '-').replace(',', '').replace(':', '').replace('.', '').replace(' //', '') + '/' + name[i].replace(' //', '').replace(' ', '-').replace(',', '').replace(':', '').replace('.', '')

    # Send empty results if no cards return from query
    if not name and not img:
        results = []
    else:
        results = zip(name, img, card_type, cmc)

    # Open deck to show how many of returned cards are in it
    deck = opendeck()

    return render_template('resultspage.html', page=page2, query="", search2=query2, results=results, index=current_page, total=page_count, urls=urls, deck=deck)

# Route for original results page


@app.route('/results/<page>', methods=['GET', 'POST'])
def results(page):
    print("Someone made a query. Showing results")
    global mySearcher
    query = ""

    # Set up stats array to be used by graphing function later
    custom_style = Style(colors=('#000000', '#FF0000', '#14FF00', '#FFFDCC', '#0004FF'))
    color = {"B": 0, "R": 0, "G": 0, "W": 0, "U": 0}
    types = {"Creature": 0, "Instant": 0, "Sorcery": 0, "Enchantment": 0, "Artifact": 0, "Legendary": 0, "Legendary Creature": 0, "Legendary Planeswalker": 0, "Land": 0}
    rare_types = {"Common": 0, "Uncommon": 0, "Rare": 0, "Mythic": 0}
    cost = {"0": 0, "1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 0, "7": 0, "8": 0, "9": 0, "10": 0, "11": 0, "12": 0, "13": 0, "14": 0, "15": 0, "16": 0}

    # Get arguments from query request
    if request.method == 'POST':
        data = request.form
    else:
        data = request.args

    # Get string from searchbox and add to query
    searchtext = data.get('searchtext')
    if searchtext is not "":
        query = searchtext

    # Collect colors from checkboxes
    colors = ""
    black = data.get('black')
    if black != None:
        colors += "B"
    green = data.get('green')
    if green != None:
        colors += "G"
    red = data.get('red')
    if red != None:
        colors += "R"
    blue = data.get('blue')
    if blue != None:
        colors += "U"
    white = data.get('white')
    if white != None:
        colors += "W"
    if colors != "":
        query = query + " colors" + colors

    # If at least one color selected, add to stats and make new graph
    if "color" in query:
        mana_graph(query, color, "colors", "stats/color.json", "Top Colors", "static/charts/mana_color_chart.svg", custom_style)
        print("updated color file")

    else:
        pass

    # Get card type from dropdown
    card_type = data.get('card_type')
    if card_type is not "":
        query = query + " type" + card_type
        # Update graph for card type
        grapher(card_type, types, "stats/types.json", "Top Types", 'static/charts/type_chart.svg')

    # Get rarity from dropdown
    rarity = data.get("rarity")
    if rarity is not "":
        query = query + " " + rarity
        # Update graph for rarity
        grapher(rarity, rare_types, "stats/rare.json", "Top Rarities", 'static/charts/rare_chart.svg')

    # Get cmc from dropdown
    cmc = data.get("cmc")
    if cmc is not "":
        query = query + " cmc" + str(cmc)
        # Update graph for converted mana cost
        grapher(cmc, cost, "stats/cost.json", "Top Cost", 'static/charts/cost_chart.svg')

    # Make query and gather resulting attributes
    name, cmc, img, card_type, set_name, current_page, page_count = mySearcher.search(query, 1)

    tcgurl = "https://shop.tcgplayer.com/magic/"
    urls = {}

    # Create url for each card using the setname and name of the card
    # Parse set and name to create url in the format needed by tcgplayer
    for i in range(len(name)):
        # If a core set, slightly different url, add set code after setname
        year = set_name[i][-2] + set_name[i][-1]
        print(set_name[i])
        if "Magic 20" in set_name[i]:
            urls[name[i]] = tcgurl + set_name[i].replace(' ', '-').replace(',', '').replace(':', '').replace('.', '').replace(' //', '') + '-m' + year + '/' + name[i].replace(' //', '').replace(' ', '-').replace(',', '').replace(':', '').replace('.', '')
        elif "Duel Decks Anthology" in set_name[i]:
            urls[name[i]] = tcgurl + set_name[i].replace(' Anthology:', '').replace(' ', '-').replace(',', '').replace(':', '').replace('.', '').replace(' //', '') + '/' + name[i].replace(' //', '').replace(' ', '-').replace(',', '').replace(':', '').replace('.', '')
        else:
            urls[name[i]] = tcgurl + set_name[i].replace(' ', '-').replace(',', '').replace(':', '').replace('.', '').replace(' //', '') + '/' + name[i].replace(' //', '').replace(' ', '-').replace(',', '').replace(':', '').replace('.', '')

    # Open deck to show how many of returned cards are in it
    deck = opendeck()

    # Send empty results if no cards return from query
    if not name and not img:
        results = []
    else:
        results = zip(name, img, card_type, cmc)

    return render_template('resultspage.html', page=1, query=searchtext, results=results, search2=query, index=current_page, total=page_count, urls=urls, deck=deck)


# Route for adding a card to deck page
@app.route('/success/', methods=['GET', 'POST'])
def success():
    print("Someone added a card to their deck")

    # Gather arguments from request
    if request.method == 'POST':
        data = request.form
    else:
        data = request.args

    # Get attributes from card added
    card_name = data['name']
    image = data['image']
    quantity = data['quantity']
    cmc = data['cmc']

    # Get card type and only store first type to be sorted in deck
    ctype = data['card_type']
    print(ctype)
    types = ctype.split("//")
    card_type = types[0]

    print(quantity, card_name, card_type, cmc, "Added to deck")

    # Add new card to stats and make new graph
    card_dict = {card_name: 1}

    card_graph(card_name, card_dict, "stats/card.json", "Top Cards", "static/charts/card_chart.svg")

    error = 0

    # Open pickle file representing the deck
    deck = opendeck()

    # Find number of cards in deck
    cardlist = []
    for card in deck:
        cardlist.append(int(deck[card][0]))

    # Set restrictions on what can go in a deck
    # Only 100 cards permited and a max of 4 of a specific card
    # Basic lands are an exception as you can have as many as you want
    if sum(cardlist) + int(quantity) <= 120:
        if card_name in deck:
            if deck[card_name][0] + int(quantity) <= 4 or "Basic Land" in ctype:
                deck[card_name][0] += int(quantity)
            else:
                error = 1
        else:
            deck[card_name] = [int(quantity), image, card_type, cmc]
    else:
        error = 1

    # Write updated deck back to pickle file
    pickle_out = open("deck.pickle", "wb")
    pickle.dump(deck, pickle_out)
    pickle_out.close()

    return render_template('addedtodeck.html', name=card_name, quantity=quantity, error=error, back=request.referrer)


# Route for deck viewing page
@app.route('/deck/', methods=['GET', 'POST'])
def deck():
    print("Someone is viewing their deck")

    # Open pickle file (deck)
    deck = opendeck()

    # Find number of cards in deck
    card_count = 0
    highestcmc = 0
    cmccount = {}
    decklist = {}
    # Create tuple list to be ordered by cmc then name
    cmcalphalist = []

    for card in deck:
        decklist[card] = str(deck[card][0]) + " " + card
        card_count += deck[card][0]
        cmcalphalist.append((int(deck[card][3].replace('cmc', '')), card))
        if int(deck[card][3].replace('cmc', '')) > highestcmc:
            highestcmc = int(deck[card][3].replace('cmc', ''))

    for i in range(9):
        cmccount[i] = 0

    sortedcards = []
    totalcmc = 0

    for card in sorted(cmcalphalist):
        sortedcards.append(card[1])
        if "Land" not in deck[card[1]][2]:
            if card[0] < 9:
                cmccount[card[0]] += 1
            else:
                cmccount[8] += 1
            totalcmc += card[0]

    avgcmc = round(float(totalcmc / len(cmcalphalist)), 2)

    # Pass in array of types for the cards to be sorted into
    types = ['Creature', 'Instant', 'Sorcery', 'Enchantment', 'Artifact', 'Planeswalker', 'Land', 'Other']

    # Gather number of cards per types
    typecount = {}

    for tp in types:
        for card in deck:
            # print(card)
            if tp in deck[card][2]:
                try:
                    typecount[tp] += deck[card][0]
                except Exception as e:
                    typecount[tp] = deck[card][0]
        if tp not in typecount:
            typecount[tp] = 0

    return render_template('deck.html', deck=deck, types=types, card_count=card_count, decklist=decklist, sortedcards=sortedcards, cmccount=cmccount, avgcmc=avgcmc, typecount=typecount)


# Route for deleting a card from deck page
@app.route('/deck/delete', methods=['GET', 'POST'])
def delete():
    print("Someone deleted a card from their deck")

    # Gather card name from request
    if request.method == 'POST':
        data = request.form
    else:
        data = request.args

    card_name = data['name']

    error = 0

    # Open pickle file (deck)
    try:
        pickle_in = open("deck.pickle", "rb")
        deck = pickle.load(pickle_in)
        pickle_in.close()
    except Exception as e:
        error = 1

    # Delete card from deck
    try:
        deck[card_name][0] = deck[card_name][0] - 1
        # If no more of deleted card, delete key from deck
        if deck[card_name][0] == 0:
            del deck[card_name]
    except Exception as e:
        error = 1

    # Write deck back to pickle file
    try:
        pickle_out = open("deck.pickle", "wb")
        pickle.dump(deck, pickle_out)
        pickle_out.close()
    except Exception as e:
        error = 1

    return render_template('delete.html', name=card_name, error=error, back=request.referrer)


# Header
@app.after_request
def add_header(response):
    # response.cache_control.no_store = True
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response


class MyWhooshSearcher(object):
    """docstring for MyWhooshSearcher"""

    def __init__(self):
        super(MyWhooshSearcher, self).__init__()

    def search(self, queryEntered, page):

        # Create list of each attribute that can be returned from the whoosh db
        name = list()
        setid = list()
        set_name = list()
        rarity = list()
        colors = list()
        cmc = list()
        mana_cost = list()
        card_type = list()
        power = list()
        toughness = list()
        text = list()
        image = list()

        # Make query on woosh db
        with self.indexer.searcher() as search:
            query = MultifieldParser(['name', 'setid', 'set_name', 'rarity', 'colors', 'cmc', 'mana_cost', 'type', 'power', 'toughness', 'text', 'img'], schema=self.indexer.schema)
            query = query.parse(queryEntered)

            results = search.search_page(query, page, pagelen=12)

            print("page: " + str(results.pagenum))
            print("page count: " + str(results.pagecount))

            # Append each returned attribute to appropriate list
            for x in results:
                # Commented out lists may be used later as new features come out
                name.append(x['name'])
                # setid.append(x['setid'])
                set_name.append(x['set_name'])
                # rarity.append(x['rarity'])
                # colors.append(x['colors'])
                cmc.append(x['cmc'])
                # mana_cost.append(x['mana_cost'])
                card_type.append(x['type'])
                # power.append(x['power'])
                # toughness.append(x['toughness'])
                # text.append(x['text'])
                image.append(x['img'])
        # Return each attribute to be used on result page
        return name, cmc, image, card_type, set_name, results.pagenum, results.pagecount

    def index(self):
        # Skip input and set reponse to no to skip this step for debugging purposes
        initial_response = input("Would you like to re-index your database? (y, n) ")
        if initial_response == 'y':
            response = input("Are you sure? If database is not set up properly, website database with be deleted. (y, n) ")
        elif initial_response == 'n':
            response = 'n'
        # response = 'n'
        if response == 'y':
            # Get password from user for their SQL db
            mySearcher.password = getpass.getpass()

            # Schema used to store attributes of each card from SQL db
            schema = Schema(id=ID(stored=True), name=TEXT(stored=True), setid=TEXT(stored=True), set_name=TEXT(stored=True), rarity=TEXT(stored=True), colors=TEXT(stored=True), cmc=TEXT(stored=True), mana_cost=TEXT(stored=True), type=TEXT(stored=True), power=TEXT(stored=True), toughness=TEXT(stored=True), text=TEXT(stored=True), img=TEXT(stored=True))
            # Create indexer for whoosh
            indexer = create_in('myIndex', schema)
            writer = indexer.writer()

            # Connect to SQL db
            # If not using local host or root as user, change this line
            conn = pymysql.connect(host='localhost', port=3306, user="root", passwd=self.password, db='MtgDb')
            cur = conn.cursor()

            # Collect all cards from db
            cur.execute("""SELECT * FROM MtgDb.MtgCards""")

            tuples = cur.fetchall()

            # For each card, add to whoosh db using the schema previously declared
            for t in tuples:
                if t[9]:
                    power = "power" + t[9]
                else:
                    power = t[9]
                if t[10]:
                    toughness = "tough" + t[10]
                else:
                    toughness = t[10]

                writer.add_document(id=t[0], name=t[1], setid=t[2], set_name=t[3], rarity=t[4], colors="colors" + t[5], cmc="cmc" + str(t[6]), mana_cost="cost" + t[7], type="type" + t[8], power=power, toughness=toughness, text=t[11], img=t[12])

            # Commit changes to whoosh db and close connection to it and the SQL db
            writer.commit()
            conn.close()
            cur.close()
            self.indexer = indexer

        # If user elects to not index whoosh db, open the previously made db
        elif response == 'n':
            self.indexer = open_dir("myIndex")

        # Exit if user inputs invalid response
        else:
            print("Invalid response. Exiting...")
            sys.exit()


if __name__ == '__main__':
    # Create searcher, index db, and start up web server
    global mySearcher
    mySearcher = MyWhooshSearcher()
    mySearcher.index()
    app.run(debug=True)
