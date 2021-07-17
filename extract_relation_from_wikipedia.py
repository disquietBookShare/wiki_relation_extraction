import argparse
import spacy
import json
import requests
import time


def write_json(x,save_path):
    json_str = json.dumps(x)
    with open(save_path, 'a+') as json_file:
        json_file.write(json_str)
        json_file.write("\n")

def get_text(text):
    return text.split(".")[0]

def spacy_ner(text,nlp):
    res=[]
    doc=nlp(text)
    for entity in doc.ents:
            res.append(str(entity))
    return res

def get_links_serface_form(annotations,text):
    res=[]
    for item in annotations:
        if item['offset'] > len(text):
            break
        res.append(item['surface_form'])
    return res

def entity_disambuigation(entity):
    tmp=[]
    min_key_len=9999
    res={}
    if isinstance(entity,dict):
        for k,v in entity.items():
            for e in v:
                if e[1]=="#####" or e[2]=="#####":
                    continue
                elif e[1]=="Wikimedia disambiguation page":
                    continue
                elif len(e)==0:
                    continue
                else:
                    tmp.append(e)
        for t in tmp:
            key=t[0]
            if len(key) < min_key_len:
                res['Qid']=key
                min_key_len=len(key)
    return res

def search_title_entity(title,timesleep):
    query = title
    url=API_ENDPOINT+"/get_task/?id="+query
    r=''
    while r == '':
        try:
            r = requests.get(url)
            break
        except:
            print("errors occur in querying ids of wikipedia title....")
            time.sleep(timesleep)
            continue
    if not r:
        return ""
    else:
        return entity_disambuigation(r.json())

def extract_relation(head,head_label,tail,tail_label,timeout):
    query = API_ENDPOINT+"/get_rel/?head=head_qid&tail=tail_qid"
    query = query.replace('head_qid', head)
    query = query.replace('tail_qid', tail)
    results = ''
    while results == '':
        try:
            # print(page, "___________________", c)
            results=requests.get(query).json()
        except:
            print("errors occur in querying relation between head and tail entities....")
            time.sleep(timeout)
            continue
        bindings = results['result']
        if bindings:
            rel = {}
            rel['em1label'] = head_label
            rel['em1Qid'] = head
            rel['em2Text'] =tail_label
            rel['em2Qid'] = tail
            rel['label'] = bindings[0]
            x['relationMentions'].append(rel)
    return x


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='wikirelaitonextraction')
    parser.add_argument('--wiki_path', type=str,help='wikipedia data path')
    parser.add_argument('--save_path', type=str, help='save_path')
    parser.add_argument('--time_out', type=int, default=3)
    parser.add_argument('--api_endpoint', type=str,default="http://39.103.225.13:8383")


    args = parser.parse_args()

    wiki_path=args.wiki_path
    save_path=args.save_path
    time_out=args.time_out
    API_ENDPOINT = args.api_endpoint

    nlp = spacy.load('en_core_web_sm')
    count = 0
    find_count = 0
    find_two_count = 0

    with open(wiki_path, "r", encoding="utf-8") as f:
        while True:
            count+=1
            line = f.readline()
            json_data = json.loads(line)
            text=get_text(json_data["text"])
            ner_results=spacy_ner(text,nlp)
            links_surface=get_links_serface_form(json_data['annotations'],text)
            links_surface.extend(ner_results)
            links_surface = list(set(links_surface))
            head_label=json_data['url'].split("/")[-1]
            if not links_surface:
                continue
            wiki_entity = search_title_entity(head_label, time_out)
            # 获取当前实体的Qid
            if not wiki_entity:
                continue
            else:
                head_Qid = wiki_entity['Qid']

            x = {}
            x['sentText'] = text
            x['relationMentions'] = []

            for tail_label in links_surface:
                tail_entity = search_title_entity(tail_label,time_out)
                if not tail_entity:
                    continue
                else:
                    tail_Qid=tail_entity['Qid']
                    x=extract_relation(head_Qid,head_label,tail_Qid,tail_label,time_out)
            if len(x['relationMentions'])>=1:
                write_json(x,save_path)
                find_count+=1
                if len((x['relationMentions']))>=2:
                    find_two_count+=1
                    print(count,find_count,find_two_count)

