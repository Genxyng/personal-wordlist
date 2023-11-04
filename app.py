import os
from datetime import datetime
from os.path import dirname, join

import requests
from bson import ObjectId
from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request, url_for
from pymongo import MongoClient

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

MONGODB_URI = os.environ.get("MONGODB_URI")
DB_NAME =  os.environ.get("DB_NAME")

client = MongoClient(MONGODB_URI)
db = client[DB_NAME]

app = Flask(__name__)


@app.route('/')
def main():
    words_result = db.words.find({}, {'_id': False})
    words = []
    for word in words_result:
        definition = word['definitions'][0]['shortdef']
        definition = definition if type(definition) is str else definition[0]
        words.append({
            'word': word['word'],
            'definition': definition,
        })
        
    return render_template(
        'index.html',
        words=words,
    )

@app.route('/detail/<keyword>')
def detail(keyword):
    api_key = '6b0708be-09cd-4683-bf7f-1ec194b80f7e'
    url = f'https://www.dictionaryapi.com/api/v3/references/collegiate/json/{keyword}?key={api_key}'
    response = requests.get(url)
    definitions = response.json()
    
    if not definitions:
        return redirect(url_for(
            'error',
            word = keyword,
            msg = f'Could not find {keyword}',
            error_type ='not_found'
        ))

    if type(definitions[0]) is str:
        suggestion = ', '.join(definitions)
        return redirect(url_for(
            'error',
            suggestions = suggestion,
            word = keyword,
            msg = f'Could not find {keyword}, did you mean: {suggestion}?',
            error_type = 'did_you_mean'
        ))
    
    status = request.args.get('status_give', 'new')
    return render_template('detail.html',word=keyword, definitions=definitions, status=status)

@app.route('/error', methods=['GET'])
def error():
    word = request.args.get('word')
    msg = request.args.get('msg')
    suggestions = request.args.get('suggestions', '').split(',')
    error_type = request.args.get('error_type')
    
    if error_type == 'not_found':
        return render_template('error.html', word=word, msg=msg)
    
    if error_type == 'did_you_mean':
        return render_template('error.html', suggestions=suggestions, word=word, msg=msg)
    
    return render_template('error.html')


@app.route('/api/save_word', methods=['POST'])
def save_word():
    json_data = request.get_json()
    word = json_data.get('word_give')
    definitions = json_data.get('definitions_give')
    
    doc = {
        'word': word,
        'definitions': definitions,
        'date': datetime.now().strftime('%Y-%m-%d')
    }
    db.words.insert_one(doc)
    return jsonify({
        'result': 'success',
        'msg': f'the word "{word}" was saved!!!'
    })
    
@app.route('/api/delete_word', methods=['POST'])
def delete_word():
    word = request.form.get('word_give')
    db.words.delete_one({'word': word})
    db.examples.delete_many({'word': word})
    return jsonify({
        'result': 'success',
        'msg': f'the word "{word}" was deleted!!!'
    })
    
@app.route('/api/get_exs', methods=['GET'])
def get_exs():
    word = request.args.get('word')
    example_data = db.examples.find({'word': word})
    examples = []
    for example in example_data:
        examples.append({
            'example': example.get('example'),
            'id': str(example.get('_id')),    
        })
        
    return jsonify({
        'result': 'success',
        'examples':examples
    })

@app.route('/api/save_ex', methods=['POST'])
def save_ex():
    word = request.form.get('word')
    example = request.form.get('example')
    doc = {
        'word': word,
        'example': example
    }
    db.examples.insert_one(doc)
    return jsonify({
        'result': 'success',
        'msg': f'your example ,{example}, for the word, {word}, was saved!'
    })

@app.route('/api/delete_ex', methods=['POST'])
def delete_ex():
    id = request.form.get('id')
    word = request.form.get('word')
    db.examples.delete_one({'_id': ObjectId(id)})
    return jsonify({
        'result': 'success',
        'msg': f'your example for the word, {word}, was deleted!'
    })

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)