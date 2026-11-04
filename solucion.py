import pandas as pd
df = pd.read_csv("candidatos.csv")
W = {
 "LI": {"centros_completados_90":.25,"duelos_def_ganados_pct":.20,"recuperaciones_90":.15,"conducciones_progresivas_90":.15,"pases_clave_90":.15,"disponibilidad_pct":.10},
 "MCD":{"intercepciones_90":.25,"precision_pase_pct":.20,"duelos_ganados_pct":.20,"pases_progresivos_90":.20,"recuperaciones_90":.15},
 "ED": {"xg_xa_90":.30,"regates_exitosos_90":.25,"pases_clave_90":.20,"tiros_puerta_90":.15,"presiones_90":.10}}
SAL = {"LI":900000,"MCD":900000,"ED":600000}
def motivos(r):
    m=[]
    if r.modalidad=="traspaso":
        if r.posicion=="ED": m.append("ED solo cesión")
        if r.coste_eur>4_000_000: m.append("traspaso > 4 M€")
        if r.coste_eur>1.2*r.valor_mercado_eur: m.append("coste > 120 % valor")
        if r.edad_01012027>27: m.append("edad > 27")
    else:
        if r.coste_eur>300_000: m.append("cesión > 300 k€")
        if r.edad_01012027>29: m.append("edad > 29 (cesión)")
    if r.salario_bruto_eur>SAL[r.posicion]: m.append("salario > tope")
    if r.dias_lesion_ult_temp>90: m.append("lesión > 90 días")
    if r.minutos_ult_temp<1200: m.append("minutos < 1.200")
    return "; ".join(m)
df["descarte"]=df.apply(motivos,axis=1)
print("DESCARTADOS:\n",df[df.descarte!=""][["jugador","posicion","descarte"]].to_string(index=False))
for pos,w in W.items():
    d=df[(df.posicion==pos)&(df.descarte=="")].copy()
    d["puntuacion"]=sum(d[c].rank(pct=True)*100*p for c,p in w.items())
    d["cat"]=pd.cut(d.puntuacion,[-1,49.99,69.99,101],labels=["C","B","A"])
    d=d.sort_values(["puntuacion","edad_01012027"],ascending=[False,True])
    print(f"\n{pos}:\n",d[["jugador","edad_01012027","extracomunitario","puntuacion","cat"]].round(1).to_string(index=False))
