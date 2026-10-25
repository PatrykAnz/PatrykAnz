import os
import requests
from pathlib import Path
from tempfile import NamedTemporaryFile
from datetime import date, timedelta

ASCII_ART = [
    "                     +S##?.                       ",
    "            ;*?+,   ;@+,?@%  :*??;                ",
    "          ,S@S*S#,  .;..?@S *@#**#%               ",
    "          %@% .%S, .:*%#@%,.@@; :S?               ",
    "    .;+:. S@S, .  +#@@#?;,,:S@S;::       :++:     ",
    "   *#SS@S,:#@#%*:,@#%@+,%##S%%S@#SS?:  :S@#S#S:   ",
    "  :@%  S@? .+%#SS?+#?%S%#S*%S%?*S#?S@+ S@%. ;@%   ",
    "   *?,.#@* .;*?#*S?*#%?S#*##%%##%@#+@S.S@% .%S;   ",
    "      .#@%:%#####*%S%##%S##%#S%%%SS%#?:#@S        ",
    " ;%SS%;+S@#S%%%#@#SS#SS%;%SSSS#SS?*##%#@#; ;?%%?: ",
    "?@S?%@@%*????%#S%S@%:       ,*#S%#S*?%%?;;S@@SS@@*",
    "#@;  ,?#SSS##S??#@*           :##?%#S%%%S@#?,  *@@",
    ";%S+  ,*%%????S##*::,.      ,::;S#S??%%S#?,  :S##*",
    "    :S#%%SSSS%?SS:;?%%?.  +%%?+:*#SS%%SS#S*   :;, ",
    "   .##%S%%%%%S#@*.??#*;, ,;+SS*:,@##%?%%?#@?      ",
    "   .S#@S..+S@#S@* ...    ,. ... :@S#@S+?#S@S      ",
    " :?+.%##,+##??S%%        ,.     +SS?%@S.S@#; *%*. ",
    ".#@*;S@S:##?S##*?,    ,:.,:     ?+#@?S@,%@#, ,*@? ",
    " +##@#?.*@###?###*     :+;,    ,#@####S ;#@#??#@+ ",
    "   ,,.,?@@#%;%@%##:   ;*+*+,  .S###?S##+.:*S#S%;  ",
    "     +#@S*,:S@%?###;   :+;.  ,S@#?##??S##S*,      ",
    "    :@@?  ,#@%*#S#%+?:     .*%%##S*S@S%S#@@#,     ",
    "    ,#@?:,:@#%#S*@S ,?%*++%#?.?#?##*S#, .+#@*     ",
    "     ;S##; +#@@#+%#.  :?SS?:  ?#+%@%S@:,SS@#,     ",
    "       .    .+S@#%??:        ,*?%#@#@?  ;*+.      ",
    "           +?: *@@###,     .+?S@@S%*:             ",
    "          ;@#,.*@@*?#S+.  .?%##+,                 ",
    "          .S@##@#?  .:?S: :###, +;                ",
    "            :+*;,    ;,S% .S@#*;#S                ",
    "                     ?SS:  .?#@#%,                ",
]

COLOR_SCHEME = {
    "background": "#0F1014",
    "title": "#be95ff",
    "key": "#E77FD6",
    "value": "#C0C0CC",
    "separator": "#777885",
    "logo_code": "#be95ff",
    "stats_title": "#7fc9d6",
    "github_stats_value": "#a4a4b1",
    "hobbies": "#67B3E6",
    "section_divider": "#585b70",
}

def calculate_age(birth_date):
    today = date.today()
    years = today.year - birth_date.year
    months = today.month - birth_date.month
    days = today.day - birth_date.day
    if days < 0:
        months -= 1
        last_month = today.replace(day=1) - timedelta(days=1)
        days += last_month.day
    if months < 0:
        years -= 1
        months += 12
    if days == 0 and months == 0:
        return f"🎂{years} years, {months} months, {days} days🎂"
    else:
        return f"{years} years, {months} months, {days} days"

def get_github_stats(username, token=None):
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
        user_response = requests.get("https://api.github.com/user", headers=headers, timeout=20)
        user_response.raise_for_status()
        username = user_response.json()["login"]
    if not username:
        username = "patrykanz"
    repos = []
    page = 1
    per_page = 100
    while True:
        url = "https://api.github.com/user/repos" if token else f"https://api.github.com/users/{username}/repos"
        params = {"page": page, "per_page": per_page, "type": "all", "sort": "updated"}
        response = requests.get(url, headers=headers, params=params, timeout=20)
        response.raise_for_status()
        page_repos = response.json()
        repos.extend(page_repos)
        if len(page_repos) < per_page:
            break
        page += 1
    total_commits = 0
    total_loc = 0
    for repo in repos:
        repo_name = repo["name"]
        owner = repo["owner"]["login"]
        contributors_url = f"https://api.github.com/repos/{owner}/{repo_name}/contributors"
        page = 1
        while True:
            contributors_response = requests.get(
                contributors_url, headers=headers,
                params={"per_page": per_page, "page": page, "anon": "false"},
                timeout=20,
            )
            contributors_response.raise_for_status()
            # Empty repositories have no contributors and return no JSON body.
            if contributors_response.status_code == 204:
                break
            contributors = contributors_response.json()
            contributor = next(
                (row for row in contributors if row.get("login", "").lower() == username.lower()),
                None,
            )
            if contributor is not None:
                total_commits += contributor.get("contributions", 0)
                break
            if len(contributors) < per_page:
                break
            page += 1
        languages_response = requests.get(
            f"https://api.github.com/repos/{owner}/{repo_name}/languages",
            headers=headers, timeout=20,
        )
        languages_response.raise_for_status()
        # ponytail: approximate LoC from language bytes; use a source scanner for exact counts.
        total_loc += sum(languages_response.json().values()) // 60
    return {"repos": len(repos), "commits": total_commits, "loc": total_loc}

def format_number(num):
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num / 1_000:.1f}K"
    return str(num)

def get_monkeytype_stats(username, ape_key=None):
    if not username:
        return None
    headers = {"Accept": "application/json"}
    if ape_key:
        headers["Authorization"] = f"ApeKey {ape_key}"
    try:
        profile_response = requests.get(
            f"https://api.monkeytype.com/users/{username}/profile",
            headers=headers,
            params={"isUid": "false"},
            timeout=20,
        )
        if profile_response.status_code != 200:
            print(f"Error: {profile_response.status_code}")
            return None
        profile_data = profile_response.json().get("data", {})
        personal_bests_data = profile_data.get("personalBests", {}).get("time", {}).get("60", [])
        rank_data = profile_data.get("allTimeLbs", {}).get("time", {}).get("60", {}).get("english", {})
        if not personal_bests_data or not rank_data:
            return None
        best_english = next(
            (
                row for row in personal_bests_data
                if row.get("language") == "english"
                and row.get("punctuation") is False
                and row.get("numbers") is False
            ),
            personal_bests_data[0],
        )
        wpm = float(best_english.get("wpm", 0))
        rank = int(rank_data.get("rank", 0))
        count = int(rank_data.get("count", 0))
        if rank <= 0 or count <= 0:
            return None
        top_percent = (rank * 100) // count
        return {"wpm": wpm, "top_percent": top_percent}
    except Exception as e:
        print(f"Error: {e}")
        return None

def generate_neofetch_svg(file_path="neofetch.svg", github_username="patrykanz", github_token=None):
    birth_date = date(2004, 1, 28)
    uptime = calculate_age(birth_date)
    github_stats = get_github_stats(github_username, github_token)
    print(f"GitHub stats: {github_stats}")
    monkeytype_username = os.getenv("MONKEYTYPE_USERNAME")
    monkeytype_ape_key = os.getenv("MONKEYTYPE_APE_KEY")
    monkeytype_stats = get_monkeytype_stats(monkeytype_username, monkeytype_ape_key)
    if monkeytype_stats:
        typing_hobby = f"Typing (MT: {monkeytype_stats['wpm']:.0f}WPM, Top {monkeytype_stats['top_percent']}%)"
    else:
        typing_hobby = "Typing (MT: 124WPM, Top 6%)"
    USER_DATA = {
        "System": "Linux Arch, Windows, macOS",
        "User": "Patryk Anzorge",
        "Role": "DevOps Engineer",
        "Certs": "Az-400, Az-104",
        "Uptime": uptime,
        "Platform": "Azure, AWS, GCP",
        "Tooling": "Terraform, Kubernetes, Python",
        "Location": "Poland",
        "Repos": str(github_stats["repos"]),
        "Commits": format_number(github_stats["commits"]),
        "LoC": format_number(github_stats["loc"]),
        "Hobbies": f"{typing_hobby} • Cycling (PB 150km in 1 day) • Gym"
    }
    ASCII_ART_COLOR = "#b4befe"
    ASCII_ART_OPACITY = 0.8
    ascii_art_lines = ASCII_ART
    ascii_svg_lines = ""
    start_y = 20
    start_x = 12
    line_height = 14.4
    for i, line in enumerate(ascii_art_lines):
        y_pos = start_y + (i * line_height)
        escaped_line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        ascii_svg_lines += f'        <text x="{start_x}" y="{y_pos}" text-anchor="start" xml:space="preserve">{escaped_line}</text>\n'
    svg_content = f"""<svg width="1000" height="450" viewBox="0 0 1000 450" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect width="1000" height="450" fill="{COLOR_SCHEME['background']}" rx="10" ry="10"/>
    <style>
        .mono {{ font: 14px 'Cascadia Code', 'JetBrains Mono', monospace; }}
        .art-mono {{ font: 12px 'Cascadia Code', 'JetBrains Mono', 'Courier New', monospace; fill: {ASCII_ART_COLOR}; opacity: {ASCII_ART_OPACITY}; white-space: pre; }}
        .title {{ fill: {COLOR_SCHEME['title']}; font-weight: bold; }}
        .key {{ fill: {COLOR_SCHEME['key']}; }}
        .value {{ fill: {COLOR_SCHEME['value']}; }}
        .separator {{ fill: {COLOR_SCHEME['separator']}; }}
        .logo-code {{ fill: {COLOR_SCHEME['logo_code']}; opacity: 0.7; }}
        .stats-title {{ fill: {COLOR_SCHEME['stats_title']}; font-weight: bold; }}
        .github-stats-value {{ fill: {COLOR_SCHEME['github_stats_value']}; font-weight: normal; }}
        .hobbies {{ fill: {COLOR_SCHEME['hobbies']}; }}
    </style>
    <g class="art-mono">
{ascii_svg_lines}    </g>
    <g class="mono" transform="translate(395, 40)">
        <text x="0" y="0" class="title">patrykanz@github</text>
        <text x="0" y="20" class="separator">{'-' * len('patrykanz@github')}</text>
        <text x="0" y="45" class="key">System:</text>
        <text x="125" y="45" class="value">{USER_DATA['System']}</text>
        <text x="0" y="65" class="key">User:</text>
        <text x="125" y="65" class="value">{USER_DATA['User']}</text>
        <text x="0" y="85" class="key">Role:</text>
        <text x="125" y="85" class="value">{USER_DATA['Role']}</text>
        <text x="0" y="105" class="key">Certs:</text>
        <text x="125" y="105" class="value">{USER_DATA['Certs']}</text>
        <text x="0" y="125" class="key">Uptime:</text>
        <text x="125" y="125" class="value">{USER_DATA['Uptime']}</text>
        <text x="0" y="145" class="key">Platform:</text>
        <text x="125" y="145" class="value">{USER_DATA['Platform']}</text>
        <text x="0" y="165" class="key">Tooling:</text>
        <text x="125" y="165" class="value">{USER_DATA['Tooling']}</text>
        <text x="0" y="185" class="key">Location:</text>
        <text x="125" y="185" class="value">{USER_DATA['Location']}</text>
        <text x="0" y="215" class="title">GitHub</text>
        <text x="0" y="225" class="separator">{'-' * len('GitHub')}</text>
        <text x="0" y="245" class="key">Repositories:</text>
        <text x="125" y="245" class="github-stats-value">{USER_DATA['Repos']}</text>
        <text x="0" y="265" class="key">Total Commits:</text>
        <text x="125" y="265" class="github-stats-value">{USER_DATA['Commits']}</text>
        <text x="0" y="285" class="key">Total LoC:</text>
        <text x="125" y="285" class="github-stats-value">{USER_DATA['LoC']}</text>
        <text x="0" y="315" class="title">Hobbies</text>
        <text x="0" y="325" class="separator">{'-' * len('Hobbies')}</text>
        <text x="0" y="350" class="hobbies">{USER_DATA['Hobbies']}</text>
        <text x="0" y="380" class="separator">*This README is automatically updated daily via GitHub Actions.*</text>
    </g>
</svg>"""
    destination = Path(file_path)
    temporary = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=destination.parent, delete=False) as f:
            temporary = Path(f.name)
            f.write(svg_content.strip())
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    print(f"Successfully generated SVG file: {file_path}")

if __name__ == "__main__":
    github_token = os.getenv("GITHUB_TOKEN")
    github_username = os.getenv("GITHUB_USERNAME", "patrykanz")
    try:
        generate_neofetch_svg(github_username=github_username, github_token=github_token)
    except requests.RequestException:
        # Public workflow logs must not expose private repository URLs from API errors.
        raise SystemExit("GitHub API request failed; existing profile stats were preserved.") from None
