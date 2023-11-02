from bs4 import BeautifulSoup
import re
import logging
import json


def get_schedule(to_json, week, year, SchoolId, Session):
    # Lectio doesn't need studentId anymore
    SCHEDULE_URL = "https://www.lectio.dk/lectio/{}/SkemaNy.aspx?week={}{}".format(SchoolId, week, year)

    schedule = Session.get(SCHEDULE_URL)

    soup = BeautifulSoup(schedule.text, features="html.parser")

    skema_table = soup.find("table", {"id": "s_m_Content_Content_SkemaNyMedNavigation_skema_skematabel"})
    day_rows = skema_table.find_all("div", {"class": "s2skemabrikcontainer lec-context-menu-instance"})
    date_rows = skema_table.find_all("tr", {"class": "s2dayHeader"})
    dates = [date.text for date in date_rows[0].find_all("td")[1:]]
    week_number = soup.find("tr", {"class": "s2weekHeader"}).text.strip()   
    schedule = {}
    for i in range(len(day_rows)):
        day_row = day_rows[i]
        skemabrikker = day_row.findAll("a", {"class": "s2skemabrik"})
        skema = {}
        # break after first iteration
        
        for brik in skemabrikker:
            input_string = brik['data-additionalinfo']
            sections = re.split(r'\n\n+', input_string)

            # Extract status (Normal! if not ændret or aflyst)
            info_section = sections[0]
            if "Ændret!" in info_section:
                status = "Ændret"
            elif "Aflyst!" in info_section:
                status = "Aflyst"
            else:
                status = "Normal"
            

            # Use regular expressions to extract other fields
            time_match = re.search(r'(\d+:\d+) - (\d+:\d+)', info_section)
            start_time, end_time = time_match.groups() if time_match else ('', '')

            team_match = re.search(r'Hold: (.+)', info_section)
            team = team_match.group(1) if team_match else ''


            teacher_match = re.search(r'Lærer: (.+)', info_section)
            teacher = teacher_match.group(1) if teacher_match else ''

            classroom_match = re.search(r'Lokale: (.+)', info_section)
            classroom = classroom_match.group(1) if classroom_match else ''

            # Extract Homework and Note sections
            homework_section = sections[1] if len(sections) > 1 else ''
            note_section = sections[2] if len(sections) > 2 else ''



            result = team.split(", ")
            for team2 in result:
                a_tag = soup.find('a', text=str(team2))
                if a_tag is None:
                    print("Not part of team " + team2)
                else:
                    href_value = a_tag.get('href')
                    match = re.search(r'holdelementid=(\d+)', href_value)
                    excrated_value = ""
                    if match:
                        extracted_value = match.group(1)
                    else:
                        return "ERROR: holdelementid not found"

                    schedule2 = Session.get("https://www.lectio.dk/lectio/{}/subnav/members.aspx?holdelementid={}&showteachers=1&showstudents=1".format(SchoolId, extracted_value))
                    soup2 = BeautifulSoup(schedule2.text, features="html.parser")
                    table = soup2.find("table", id="s_m_Content_Content_laerereleverpanel_alm_gv")
                    rows = table.findAll("tr")
                    rows.pop(0)
                    members = []
                    for row in rows: #for each member
                        memberinfo = row.findAll("td")
                        image = memberinfo[0].find("img", title="Vis større foto")
                        image = image.get('src')
                        def filter_by_id(tag):
                            return tag.has_attr('id') and 's_m_Content_Content_laerereleverpanel_alm_gv_ct' in tag['id']
                        def check_and_append(lst, obj):
                            for element in lst:
                                if element == obj:
                                    return
                            lst.append(obj)
                        name = memberinfo[3].find(filter_by_id)
                        last_name = memberinfo[4].find("span", class_="noWrap")
                        teacher_or_student = memberinfo[1]
                        check_and_append(members, {
                            "image": "https://lectio.dk" + str(image),
                            "full_name": name.text + " " + last_name.text,
                            "type": teacher_or_student.text
                        })
                

            # check if a class with the same team already exists in the schedule
            if team in skema:
                skema[str(team) + "2"] = {
                    "status": status,
                    "start_time": start_time,
                    "end_time": end_time,
                    "teacher": teacher,
                    "classroom": classroom,
                    "homework": homework_section.strip(),
                    "note": note_section.strip(),
                    "members": members
                }
            
            # Print the parsed information
            else:
                skema[team] = {
                    "status": status,
                    "start_time": start_time,
                    "end_time": end_time,
                    "teacher": teacher,
                    "classroom": classroom,
                    "homework": homework_section.strip(),
                    "note": note_section.strip(),
                    "members": members
                }

        schedule[dates[i]] = skema
    if to_json:
        with open('schedule.json', 'w') as fp:
            json.dump(schedule, fp, indent=4)
    return schedule
