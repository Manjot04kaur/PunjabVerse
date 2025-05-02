from flask import Flask, render_template, request, jsonify
import sqlite3
from rapidfuzz import fuzz
import re
from unidecode import unidecode  # For basic romanization handling

app = Flask(__name__)

def get_all_proverbs():
    conn = sqlite3.connect('proverbs (1).db')
    cursor = conn.cursor()
    cursor.execute("SELECT Punjabi_Idiom, English_Transliteration, English_meaning, Equivalent_English_Idiom FROM proverbs")
    results = cursor.fetchall()
    conn.close()
    return results

def transliterate_romanized_to_gurmukhi(query):
    gurmukhi_query = unidecode(query)  
    return gurmukhi_query 

def get_dynamic_threshold(query):
    length = len(query)
    is_romanized = all(ord(char) < 128 for char in query)

    if not is_romanized:
        if length <= 3:
            return 30  
        elif length <= 60:
            return 60
        else:
            return 70
    else:
        if length <= 3:
            return 50
        elif length <= 60:
            return 65
        else:
            return 75

def fuzzy_search_partial(keyword):
    threshold = get_dynamic_threshold(keyword)
    all_rows = get_all_proverbs()
    matches = []
    for row in all_rows:
        punjabi, romanized, meaning, equivalent = row
        punjabi_score = fuzz.partial_ratio(keyword, punjabi)
        romanized_score = fuzz.partial_ratio(keyword, romanized if romanized else "")
        meaning_score = fuzz.partial_ratio(keyword, meaning)
        equivalent_score = fuzz.partial_ratio(keyword, equivalent if equivalent else "")
        
        if max(punjabi_score, romanized_score, meaning_score, equivalent_score) >= threshold:
            matches.append((punjabi, romanized, meaning, equivalent))
    return matches[:10]

@app.route('/', methods=['GET', 'POST'])
def index():
    results = []
    keyword = ""
    message = ""

    if request.method == 'POST':
        keyword = request.form['query'].strip()
        selected = request.form.get('selected', 'false') == 'true'

        if keyword:
            all_rows = get_all_proverbs()
            normalized_keyword = keyword.lower()
            is_romanized = all(ord(char) < 128 for char in keyword)
            standardized_query = keyword.lower()
            exact_results = [
                row for row in all_rows
                if row[0].lower() == standardized_query or (row[1] and row[1].lower() == standardized_query)
            ]

            if exact_results:
                results = exact_results
            else:
                if not selected:
                    if is_romanized:
                        message = "Please select from suggestions rather than searching manually."
                    else:
                        message = "Please try again or check the spelling."
                    results = []
                else:
                    results = fuzzy_search_partial(standardized_query)
                    if not results:
                        if is_romanized:
                            message = "For Romanized Punjabi, please select from suggestions rather than searching manually."
                        else:
                            message = "It looks like the proverb is not present in the database."
                # if not results and is_romanized:
                #     gurmukhi_translation = transliterate_romanized_to_gurmukhi(standardized_query)
                #     if gurmukhi_translation:
                #         all_rows = get_all_proverbs()
                #         results = [row for row in all_rows if row[0] == gurmukhi_translation]
                #         if not results:
                #             message = "No matching proverb found after transliteration."

    return render_template('damo1 (2).html', results=results, keyword=keyword, message=message)

@app.route('/suggest', methods=['GET'])
def suggest():
    query = request.args.get('q', '').strip()
    suggestions = []

    if not query:
        return jsonify([])

    threshold = get_dynamic_threshold(query)
    all_rows = get_all_proverbs()
    is_romanized = all(ord(char) < 128 for char in query)
    query_lower = query.lower()

    for row in all_rows:
        punjabi = row[0]
        romanized = row[1] if row[1] else ""

        punjabi_match = punjabi.strip()
        romanized_match = romanized.lower().strip()

        if is_romanized:
            if romanized_match.startswith(query_lower):
                score = 100
            elif query_lower in romanized_match.split():
                score = 90
            else:
                score = fuzz.token_set_ratio(query_lower, romanized_match)

            if score >= threshold:
                suggestions.append((romanized, score))

        else:
            if punjabi_match.startswith(query):
                score = 100
            elif query in punjabi_match.split():
                score = 90
            else:
                score = fuzz.WRatio(query, punjabi_match)

            if score >= threshold:
                suggestions.append((punjabi, score))

    suggestion_dict = {}
    for text, score in suggestions:
        if text not in suggestion_dict or score > suggestion_dict[text]:
            suggestion_dict[text] = score

    final = [item[0] for item in sorted(suggestion_dict.items(), key=lambda x: -x[1])][:10]

    return jsonify(final)

if __name__ == '__main__':
    app.run(debug=True)
