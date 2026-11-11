import sys
import os

sys.path.insert(0, r"D:\OneDrive\04_Desarrollo_proyectos\0000_Utilidades\03_OneNote")
import graph_api

def main():
    print("Iniciando validación de páginas de OneNote en todos los proyectos...")
    nbs = graph_api.get_notebooks()
    target_group = next(g for g in graph_api.get_section_groups(nbs[0]["id"]) if "desarrollo" in g["displayName"].lower())
    secs = graph_api.get_sections_in_group(target_group["id"])
    
    all_ok = True
    print(f"Grupo encontrado: {target_group['displayName']} con {len(secs)} secciones.")
    print("-" * 60)
    
    for s in secs:
        pages = graph_api.get_pages(s["id"])
        titles = [p["title"] for p in pages]
        has_01 = any("01. resumen" in t.lower() for t in titles)
        has_02 = any("02. listado" in t.lower() for t in titles)
        has_03 = any("siguientes pasos" in t.lower() for t in titles)
        
        status = "✅ OK" if (has_01 and has_02 and has_03) else "❌ INCOMPLETO"
        if not (has_01 and has_02 and has_03):
            all_ok = False
            
        print(f"[{status}] Sección: {s['displayName']}")
        for idx, t in enumerate(titles, 1):
            print(f"      {idx}. {t}")
        print()
        
    print("-" * 60)
    if all_ok:
        print("RESULTADO GLOBAL: TODAS LAS SECCIONES TIENEN LA HOJA DE 'SIGUIENTES PASOS' Y EL ORDEN CANONICO.")
    else:
        print("RESULTADO GLOBAL: SE ENCONTRARON FALLOS O SECCIONES INCOMPLETAS.")

if __name__ == "__main__":
    main()
