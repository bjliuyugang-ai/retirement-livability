#!/usr/bin/env python3
"""Decrypt the official public permit page's AES-ECB display payloads."""
import base64,csv,json,re,pathlib,html
from datetime import datetime,timezone
from html.parser import HTMLParser
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

ROOT=pathlib.Path("research_engine/retirement/national_funnel/R4_ENVIRONMENT_236/POLLUTION_PERMIT_DISCOVERY/output")
FILES=sorted(ROOT.glob("details_*.html"))
class Text(HTMLParser):
 def __init__(self):super().__init__();self.parts=[]
 def handle_data(self,d):
  x=" ".join(d.split())
  if x:self.parts.append(x)
def main():
 results=[]
 for p in FILES:
  s=p.read_text(encoding="utf-8",errors="replace")
  pwdm=re.search(r"var\s+pwd\s*=\s*'([^']+)'",s)
  wordm=re.search(r"var\s+word\s*=\s*'([^']+)'",s)
  lon=re.search(r'id="longitude"\s+value="([^"]+)"',s)
  lat=re.search(r'id="latitude"\s+value="([^"]+)"',s)
  tp=Text();tp.feed(s);txt=" ".join(tp.parts)
  def after(label):
   m=re.search(re.escape(label)+r"\s*([^<\r\n]+)",txt)
   return html.unescape(m.group(1)).strip() if m else None
  row={"file":p.name,"longitude":lon.group(1) if lon else None,"latitude":lat.group(1) if lat else None,
       "address":after("生产经营场所地址："),"industry":after("行业类别："),"admin":after("所在地区："),
       "air_pollutants":after("大气主要污染物种类："),"water_pollutants":after("废水主要污染物种类："),
       "decrypt_status":"NO_ENCRYPTED_PAYLOAD"}
  if pwdm and wordm:
   try:
    key=pwdm.group(1).encode("utf-8")
    ciphertext=base64.b64decode(wordm.group(1))
    plaintext=unpad(AES.new(key,AES.MODE_ECB).decrypt(ciphertext),AES.block_size).decode("utf-8","replace")
    row["decrypt_status"]="SUCCESS";row["decrypted_chars"]=len(plaintext)
    try:
     parsed=json.loads(plaintext);row["payload_type"]="JSON";row["payload"]=parsed
    except Exception:
     row["payload_type"]="TEXT";row["payload_text"]=plaintext[:30000]
   except Exception as e:
    row["decrypt_status"]="FAILED";row["decrypt_error"]=repr(e)
  results.append(row)
 out={"schema":"MEE_PUBLIC_PERMIT_DECRYPTED_DETAIL_V1","created_at_utc":datetime.now(timezone.utc).isoformat(),
      "source_files":len(FILES),"results":results}
 (ROOT/"permit_detail_decrypted_payloads.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("DECRYPT_RESULTS",json.dumps([{"file":x["file"],"status":x["decrypt_status"],"type":x.get("payload_type"),"chars":x.get("decrypted_chars"),"address":x.get("address"),"coords":[x.get("longitude"),x.get("latitude")]} for x in results],ensure_ascii=False),flush=True)
if __name__=="__main__":main()
