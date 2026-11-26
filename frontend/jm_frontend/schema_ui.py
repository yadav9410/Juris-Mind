import json
import streamlit as st
def resolve_ref(schema,openapi):
    if not isinstance(schema,dict):return {}
    ref=schema.get("$ref")
    if not ref:return schema
    node=openapi or {}
    for part in ref.lstrip("#/").split("/"):node=node.get(part,{})
    return node if isinstance(node,dict) else {}
def render_operation_form(schema,name,required,key,openapi=None):
    schema=resolve_ref(schema,openapi or st.session_state.get("openapi") or {})
    typ=schema.get("type","string");fmt=schema.get("format");enum=schema.get("enum")
    title=(schema.get("title") or name.replace("_"," ").capitalize())+(" *" if required else "")
    desc=schema.get("description")
    if enum:
        opts=list(enum);default=schema.get("default",opts[0] if opts else None)
        idx=opts.index(default) if default in opts else 0
        return st.selectbox(title,opts,index=idx,key=key,help=desc)
    if typ=="boolean":return st.checkbox(title,value=bool(schema.get("default",False)),key=key,help=desc)
    if typ=="integer":
        return st.number_input(title,value=int(schema.get("default",0) or 0),step=1,key=key,help=desc)
    if typ=="number":
        return st.number_input(title,value=float(schema.get("default",0.0) or 0.0),key=key,help=desc)
    if typ=="array":
        raw=st.text_area(title,value=json.dumps(schema.get("default",[])),key=key,help=(desc or "Enter a JSON array."))
        try:return json.loads(raw)
        except Exception:st.warning(f"{name}: enter a valid JSON array.");return None
    if typ=="object":
        raw=st.text_area(title,value=json.dumps(schema.get("default",{})),key=key,help=(desc or "Enter a JSON object."))
        try:return json.loads(raw)
        except Exception:st.warning(f"{name}: enter a valid JSON object.");return None
    default=schema.get("default")
    if fmt=="date":return st.date_input(title,key=key,help=desc).isoformat()
    if fmt=="date-time":return st.text_input(title,value=str(default or ""),key=key,help=desc,placeholder="YYYY-MM-DDTHH:MM:SS")
    maxlen=schema.get("maxLength",0)
    multiline=maxlen>180 or name.lower() in {"text","content","description","reason","summary","passage","proposition","body"}
    if multiline:return st.text_area(title,value=str(default or ""),key=key,help=desc,height=110)
    return st.text_input(title,value=str(default or ""),key=key,help=desc,placeholder=desc or "")
def operation_summary(op):
    return op.get("summary") or op.get("operationId") or "API operation"
