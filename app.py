from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/guides')
def guides():
    return render_template('guides.html') 

@app.route('/characters')
def characters():
    return render_template('characters.html')
    
@app.route('/map')
def map():
    return render_template('map.html')

if __name__ == '__main__':
    app.run(debug=True)
