from bs4 import BeautifulSoup
import os
import re
import json
import arabic_reshaper
from bidi.algorithm import get_display





def extract_topic_counts(folder, outfp):
    """Extract the topic counts from each html page.

    NB:
    1. in pre-Nov 2011 html pages, the topics are in a table;
       from Nov 2011 onwards, they are in an unordered list (<ul>)
    2. some category numbers changed over the years;
       best to use the category names instead as keys
    """
    topic_d = dict()
    for fn in os.listdir(folder):
        if fn.endswith("html"):
            print(fn)
            fp = os.path.join(folder, fn)
            try:
                with open(fp, mode="r", encoding="utf-8") as file:
                    text = file.read()
            except:
                with open(fp, mode="r") as file:
                    text = file.read()
            soup = BeautifulSoup(text)
            date = int(fn[:8])
            d = dict()
            print(date)
            if date < 20101100:
                tds = soup.find_all("td", class_="row1")
                print(len(tds))
    ##            topic_tds = []
    ##            for td in tds:
    ##                if
                tds = [td for td in tds if td.a and \
                       ("cat=" in td.a["href"] or "cid=" in td.a["href"])]
                print(len(tds))
                for td in tds:
                    cat_name = td.a.get_text().strip()
                    cat_no = re.findall("c\w\w=(\d+)", td.a["href"])[0]
                    count = td.find_next_sibling("td").get_text().strip()
                    print(cat_no, cat_name, count)
                    d[cat_no] = {"cat_name": cat_name, "count": int(count)}
            else:
                print("later date")
                lis = soup.find_all("li", class_="regular-cat")
                for li in lis:
                    cat_name = li.a.get_text().strip()
                    cat_no = re.findall("category/(\d+)", li.a["href"])[0]
                    #print(li.span)
                    count = re.findall("عدد الكتب: *(\d+)", li.span.get_text())[0]
                    print(cat_no, cat_name, count)
                    d[cat_no] = {"cat_name": cat_name, "count": int(count)}
            topic_d[date] = d
    with open(outfp, mode="w", encoding="utf-8") as file:
        json.dump(topic_d, file, ensure_ascii=False, indent=2)
    return topic_d

def get_totals(topic_d):
    totals = dict()
    for k, d in sorted(topic_d.items()):
        #total = sum([d[cat]["count"] for cat in d])
        total = 0
        for cat in d:
            #print(d[cat], [d[cat]["count"]])
            total += int(d[cat]["count"])
        print(k, total)
        totals[k] = total
    return totals

def check_categories(topic_d):
    """Check whether the category numbers remain the same over time.

    Result: no they don't, so better use the category names as dictionary keys."""
    cat_dict = dict()
    for k, d in sorted(topic_d.items()):
        for cat_no in d:
            if cat_no not in cat_dict:
                cat_dict[cat_no] = set()
            cat_dict[cat_no].add(d[cat_no]["cat_name"])
    return cat_dict

def merge_topics(topic_d):
    new = dict()
    for date in topic_d:
        n = dict()
        for cat, count in topic_d[date].items():
            cat = cat.split("-")[0].strip()
            cat = re.sub("^كتب ", "", cat).strip()
            cat = re.sub(r"\bال", "", cat).strip()
            cat = re.sub(r"\bوال", "و", cat).strip()
            cat = re.sub("^تيمية$", "ابن تيمية", cat)
            if cat not in n:
                n[cat] = 0
            n[cat] += int(count)
        new[date] = n
    return new
            

def create_time_series(topic_d):
    """
    Returns:
        dict (k: topic, v: list of counts)
    """
    all_topics = set()
    for date, d in topic_d.items():
        for topic in d:
            all_topics.add(topic)
    all_topics = {t: [] for t in all_topics}
    for t in all_topics:
        series = []
        for date, d in sorted(topic_d.items()):
            if t in d:
                series.append(str(d[t]))
            else:
                series.append("0")
        all_topics[t] = series
    return all_topics

def create_gifs(csv_fp, outfp):
    import matplotlib.animation as ani
    import matplotlib.pyplot as plt
    from matplotlib.font_manager import FontProperties
    import numpy as np
    import pandas as pd

    def reshape(s):
        return get_display(arabic_reshaper.reshape(s))

    df = pd.read_csv(csv_fp, delimiter="\t", header=0)
    df_ix = df.set_index("Topic")
##    print(df_ix.columns)
##    print(df_ix.index)
##    input()
    # transpose the dataframe so that the row indexes become the dates: 
    df_tr = df_ix.T
    df_tr.index=pd.to_datetime(df_tr.index, format="%Y%m%d")
    df_tr.columns = [reshape(c) for c in df_tr.columns]
##    print(df_tr.columns)
##    print(df_tr.index)

    fig, ax = plt.subplots()
    fig.set_size_inches(10, 6)
    fig.subplots_adjust(left=0.2)

    font = FontProperties()
    font.set_name('Times New Roman')
    font.set_size("14")
    
    cmap = plt.cm.get_cmap("jet", len(list(df_tr.columns.values)))
    colors = {genre: cmap(i) \
              for i, genre in enumerate(list(df_tr.columns.values))}
    max_val = df_tr.values.max()+100 # largest value in the dataframe
    print(max_val)

    def build_bar_chart(frame):
        temp_df = df_tr.sort_values(by=df_tr.index[frame],
                                    axis=1, ascending=False)
        max_objects = 20
        objects = list(temp_df.columns.values)[:max_objects]
        vals = list(temp_df.iloc[frame])[:max_objects]
        ax.clear()
        c = [colors[g] for g in objects[::-1]]
        plt.barh(objects[::-1], vals[::-1], color=c)
        plt.ylabel("Topic")
        plt.xlabel("Number of Books")
        plt.yticks(objects, fontproperties=font)
        plt.xticks([x*100 for x in range(20) if x*100 < max_val])
        for i, v in enumerate(vals[::-1]):
            ax.text(v+10, i, str(v), color="black",
                    ha="left", va="center", fontsize=12)
        title = "Shamela collection evolution: {}".format(df_tr.index[frame])
        plt.title(title[:-9])
        #plt.autoscale()
    animator = ani.FuncAnimation(fig, build_bar_chart,
                                 range(len(df_tr.index)), interval=1000)
    w = ani.PillowWriter(fps=0.5)
    animator.save(outfp, writer=w)
##    W = ani.writers["ffmpeg"]
##    animator.save(r'ShamelaEvolution.mp4', writer=W(fps=2))
    plt.show()
    


if __name__ == "__main__":  
    folder = "."
    fp = "topic_counts.json"

    # extract the topic counts into a dictionary:
##    topic_d = extract_topic_counts(folder, fp)
    
    with open(fp, mode="r", encoding="utf-8") as file:
        topic_d = json.load(file)

##    totals = get_totals(topic_d)

##    cat_dict = check_categories(topic_d)
##    for cat in sorted(cat_dict):
##        if len(cat_dict[cat]) > 1:
##            print(cat, cat_dict[cat])

    # use cat_name as key in the topic_d:
    topic_d = {k:{d[k2]["cat_name"]: d[k2]["count"] for k2 in d} for k, d in topic_d.items()}

    topic_d = merge_topics(topic_d)

##    for k in sorted(topic_d):
##        #print(k)
##        for k2 in topic_d[k]:
##            print(k, k2, " "*(40-len(k2)), topic_d[k][k2])

    time_series = create_time_series(topic_d)
##    print(" "*40, "\t".join(sorted(topic_d.keys())))
##    for topic, series in time_series.items():
##        #print(topic)
##        print(topic, " "*(40-len(topic)), "\t".join(series))
    csv_fp = "shamela_ws_topics_time_series.tsv"
##    with open(csv_fp, mode="w", encoding="utf-8") as file:
##        file.write("Topic\t" + "\t".join(sorted(topic_d.keys())) + "\n")
##        for topic, series in sorted(time_series.items()):
##            file.write(topic + "\t" + "\t".join(series) + "\n")
    create_gifs(csv_fp, r'ShamelaEvolution_w_labels.gif')
            
        
    
    
    

