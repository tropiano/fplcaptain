# all the imports
from flask import Flask, g, render_template, send_file, jsonify, session, abort, request, flash, redirect, url_for
import requests
import os
import itertools
from PIL import Image, ImageDraw, ImageFont

# from wtforms import Form, BooleanField, StringField, FloatField, DateField, IntegerField, validators


app = Flask(__name__)  # create the application instance :)
app.config.from_object(__name__)
# uncomment to test locally
# app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://localhost/fpl'
# db.Model.metadata.reflect(db.engine)
app.secret_key = 'T5%&/yHDfSTs'


# calculations
def calculate_stats(team_id):

    team_url = "https://fantasy.premierleague.com/api/entry/"+team_id+"/"
    gw_url = "https://fantasy.premierleague.com/api/entry/"+team_id+"/event/"
    fpl_url = "https://fantasy.premierleague.com/api/bootstrap-static/"
    transfers_url = "https://fantasy.premierleague.com/api/entry/"+team_id+"/transfers"
    player_url = "https://fantasy.premierleague.com/api/element-summary/"

    r = requests.get(team_url)
    entry = r.json()

    team_name = entry["name"]
    user_name = entry["player_first_name"] + " " + entry["player_last_name"]
    total_points = entry["summary_overall_points"]

    r = requests.get(fpl_url)
    jsonResponse = r.json()
    elements = jsonResponse['elements']
    stats = jsonResponse['element_stats']
    players = jsonResponse['total_players']

    players = []
    for e in elements:
        player = {}

        player['name'] = e['web_name']
        player['assists'] = e['assists']
        player['goals_scored'] = e['goals_scored']
        player['creativity'] = e['creativity']
        player['threat'] = e['threat']
        player['role'] = e['element_type']
        player['id'] = e['id']

        players.append(player)

    player_id_name = {}
    for p in players:
        player_id_name[p["id"]] = p["name"]

    stats_all = []

    i = 1
    r = requests.get(gw_url + str(i) + "/picks/")
    while r.status_code == 200:
        stats_gw = {}
        url = gw_url + ""
        jsonResponse = r.json()
        picks = jsonResponse['picks']
        stats_gw["gw"] = i
        stats_gw["stats"] = picks
        stats_all.append(stats_gw)
        i += 1
        r = requests.get(gw_url + str(i) + "/picks/")

    captain_stats = []
    for s in stats_all:
        cap_stat = {}
        stats = s["stats"]
        # print(stats)
        for ss in stats:
            if ss["multiplier"] == 2:
                cap_stat["id"] = ss["element"]
                cap_stat["gw"] = s["gw"]
                captain_stats.append(cap_stat)

    full_captain_stats = []

    for c in captain_stats:
        full_stat = {}
        full_stat["id"] = c["id"]
        full_stat["gw"] = c["gw"]
        r = requests.get(player_url+str(c["id"])+"/")
        jsonResponse = r.json()
        stats = []
        for gw in jsonResponse['history']:
            if str(gw["round"]) == str(full_stat["gw"]):
                full_stat["points"] = gw["total_points"]
                full_stat["minutes"] = gw["minutes"]
                full_stat["goals"] = gw["goals_scored"]
                full_stat["assists"] = gw["assists"]
                full_stat["bonus"] = gw["bonus"]
                full_stat["name"] = player_id_name[c["id"]]
                break
        full_captain_stats.append(full_stat)

    cap_points = []
    full_captain_stats_sort = sorted(
        full_captain_stats, key=lambda x: x["name"])
    for key, group in itertools.groupby(full_captain_stats_sort, key=lambda x: x["name"]):
        cap_points.append((key, sum((x["points"] for x in list(group)))))

    cap_points_sort = sorted(cap_points, key=lambda x: x[1], reverse=True)

    all_stats = dict()
    all_stats["total_points"] = total_points
    all_stats["cap_points"] = cap_points_sort
    all_stats["team_name"] = team_name
    all_stats["team_id"] = team_id
    all_stats["user_name"] = user_name

    return all_stats


def create_graphic(all_stats):

    team_id = all_stats["team_id"]
    cap_points_sort = all_stats["cap_points"]
    team_name = all_stats["team_name"]
    user_name = all_stats["user_name"]
    total_points = all_stats["total_points"]

    size = 1024, 512
    color_white = 'rgb(255, 255, 255)'
    filename = os.path.join(app.root_path, 'static',
                            'images/fpl_cap_info_{}.png'.format(team_id))
    mode = "RGB"

    img = Image.new(mode, size, color_white)
    img_logo = Image.open(os.path.join(app.root_path, 'static',
                                       'images/premier-league-logo.png'))
    logo_size_w, logo_size_h = img_logo.size
    img_logo_small = img_logo.resize((int(logo_size_w/2), int(logo_size_h/2)))

    img.paste(img_logo_small, box=(850, 350))

    # initialise the drawing context with
    # the image object as background
    draw = ImageDraw.Draw(img)

    # define the fonts
    font = ImageFont.truetype(os.path.join(app.root_path, 'static',
                                           'fonts/Roboto-Bold.ttf'), size=65)
    font_medium = ImageFont.truetype(os.path.join(app.root_path, 'static',
                                                  'fonts/Roboto-Bold.ttf'), size=50)
    font_small = ImageFont.truetype(os.path.join(app.root_path, 'static',
                                                 'fonts/Roboto-Bold.ttf'), size=25)
    font_verysmall = ImageFont.truetype(os.path.join(app.root_path, 'static',
                                                     'fonts/Roboto-Bold.ttf'), size=15)

    color = 'rgb(203, 67, 53)'  # red color
    color_blue = 'rgb(33, 97, 140)'  # red color

    message = "Best captains"
    draw.text((50, 20), message, fill=color, font=font_medium)

    left_x_name = 60
    bar_offset = 470
    bar_width = 150
    bar_space = 10
    text_space = 30

    player_name = cap_points_sort[0][0]
    points = cap_points_sort[0][1]
    message = str(points) + " pts"
    ratio = 350./points
    draw.rectangle(((50, bar_offset-ratio*points),
                    (50+bar_width, bar_offset)), fill='rgb(203, 67, 53)')
    (x, y) = (left_x_name, bar_offset-ratio*points+text_space)
    draw.text((x, y), message, fill=color_white, font=font_small)
    (x, y) = (left_x_name, bar_offset-ratio*points)
    draw.text((x, y), player_name, fill=color_white, font=font_small)

    if len(cap_points_sort) > 1:
        player_name = cap_points_sort[1][0]
        points = cap_points_sort[1][1]
        message = str(points) + " pts"
        draw.rectangle(((50+bar_width+bar_space, bar_offset-ratio*points),
                        (50+bar_space+2*bar_width, bar_offset)), fill='rgb(203, 67, 53)')
        (x, y) = (left_x_name+bar_width+bar_space,
                  bar_offset-ratio*points+text_space)
        draw.text((x, y), message, fill=color_white, font=font_small)
        (x, y) = (left_x_name+bar_width+bar_space, bar_offset-ratio*points)
        draw.text((x, y), player_name, fill=color_white, font=font_small)

    if len(cap_points_sort) > 2:
        player_name = cap_points_sort[2][0]
        points = cap_points_sort[2][1]
        message = str(points) + " pts"
        draw.rectangle(((50+2*bar_width+2*bar_space, bar_offset-ratio*points),
                        (50+2*bar_space+3*bar_width, bar_offset)), fill='rgb(203, 67, 53)')
        (x, y) = (left_x_name+2*bar_width+2 *
                  bar_space, bar_offset-ratio*points+text_space)
        draw.text((x, y), message, fill=color_white, font=font_small)
        (x, y) = (left_x_name+2*bar_width+2*bar_space, bar_offset-ratio*points)
        draw.text((x, y), player_name, fill=color_white, font=font_small)

    (x, y) = (580, 150)
    message = "Points from captains "
    draw.text((x, y), message, fill=color, font=font_small)
    message = str(sum([2*x[1] for x in cap_points_sort]))
    (x, y) = (580, 200)
    draw.text((x, y), message, fill=color, font=font)
    points_ratio = round(float(message)/total_points, 3)*100
    message = str(round(points_ratio, 2)) + "% of the total"
    (x, y) = (580, 265)
    draw.text((x, y), message, fill=color, font=font_small)

    draw.text((730, 20), team_name, fill=color_blue, font=font_small)
    draw.text((730, 60), user_name, fill=color_blue, font=font_small)

    (x, y) = (650, 430)
    message = "by @ItaliaFpl"
    draw.text((x, y), message, fill=color_blue, font=font_small)

    img.save(filename)

# views


@app.route('/')
def home_page():

    return render_template('index.html')


@app.route('/', methods=['POST'])
def show_infographic():

    team_id = request.form['teamid']

    return redirect(url_for('captain_info', team_id=team_id))


@app.route('/cap_stats/<team_id>')
def captain_info(team_id):

    try:
        captain_stats = calculate_stats(team_id)
        create_graphic(captain_stats)

    except Exception as e:
        print(e)
        flash('Team Id not found, sorry', 'error')
        return redirect(url_for('home_page'))

    return render_template('cap_stats.html', team_id=team_id)
