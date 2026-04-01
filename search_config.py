from __future__ import annotations

# Términos vacíos o poco útiles para la similitud.
STOPWORDS = {
    "a",
    "al",
    "con",
    "de",
    "del",
    "el",
    "en",
    "excepto",
    "la",
    "las",
    "los",
    "o",
    "otras",
    "otros",
    "otra",
    "otro",
    "para",
    "por",
    "sin",
    "u",
    "y",
    "e",
}

# Expansiones semánticas del lado del query. La idea es acercar lenguaje común
# o del SAT a la terminología SCIAN aunque no coincida literalmente.
QUERY_EXPANSIONS = {
    "restaurante": "preparacion alimentos bebidas fonda cocina",
    "restaurantes": "preparacion alimentos bebidas fonda cocina",
    "cafeteria": "cafe preparacion alimentos bebidas",
    "cafeterias": "cafe preparacion alimentos bebidas",
    "taqueria": "restaurante preparacion alimentos bebidas tacos",
    "taquerias": "restaurante preparacion alimentos bebidas tacos",
    "fonda": "restaurante preparacion alimentos bebidas",
    "loncheria": "restaurante preparacion alimentos bebidas",
    "bar": "bebidas alcoholicas preparacion alimentos bebidas cantina",
    "cantina": "bebidas alcoholicas preparacion alimentos bebidas bar",
    "abarrotes": "tienda ultramarinos miscelanea despensa",
    "minisuper": "abarrotes tienda conveniencia miscelanea",
    "miscelanea": "abarrotes ultramarinos tienda conveniencia",
    "farmacia": "comercio productos farmaceuticos naturistas medicamentos botica",
    "farmacias": "comercio productos farmaceuticos naturistas medicamentos botica",
    "dentista": "consultorio dental odontologia",
    "dentistas": "consultorio dental odontologia",
    "odontologo": "consultorio dental odontologia",
    "odontologos": "consultorio dental odontologia",
    "doctor": "consultorio medico",
    "doctores": "consultorio medico",
    "medico": "consultorio medico",
    "medicos": "consultorio medico",
    "psicologo": "consultorio psicologia terapia",
    "psicologos": "consultorio psicologia terapia",
    "veterinaria": "servicios veterinarios mascotas",
    "veterinarias": "servicios veterinarios mascotas",
    "estetica": "salones y clinicas de belleza peluqueria barberia",
    "esteticas": "salones y clinicas de belleza peluqueria barberia",
    "barberia": "salones y clinicas de belleza peluqueria estetica",
    "barberias": "salones y clinicas de belleza peluqueria estetica",
    "papeleria": "comercio articulos de papelera articulos de papeleria utiles escolares oficina libros revistas periodicos",
    "papelerias": "comercio articulos de papelera articulos de papeleria utiles escolares oficina libros revistas periodicos",
    "ferreteria": "comercio ferreteria tlapaleria herramientas herrajes",
    "ferreterias": "comercio ferreteria tlapaleria herramientas herrajes",
    "software": "edicion de software programacion sistemas computo",
    "app": "software programacion sistemas computo",
    "apps": "software programacion sistemas computo",
    "aplicacion": "software programacion sistemas computo",
    "aplicaciones": "software programacion sistemas computo",
    "fletes": "autotransporte carga paqueteria logistica",
    "paqueteria": "mensajeria paqueteria carga logistica",
    "taller": "reparacion mecanica automotriz",
    "mecanico": "reparacion mecanica automotriz",
    "mecanicos": "reparacion mecanica automotriz",
    "hotel": "alojamiento temporal hospedaje",
    "hoteles": "alojamiento temporal hospedaje",
    "guarderia": "guarderias estancia infantil",
    "guarderias": "guarderias estancia infantil",
    "gimnasio": "acondicionamiento fisico fitness gimnasio gimnasio deportivo",
    "gimnasios": "acondicionamiento fisico fitness gimnasio gimnasio deportivo",
    "panaderia": "elaboracion de pan pasteleria reposteria",
    "panaderias": "elaboracion de pan pasteleria reposteria",
    "tortilleria": "tortillas de maiz nixtamal masa",
    "tortillerias": "tortillas de maiz nixtamal masa",
    "carniceria": "comercio carnes",
    "carnicerias": "comercio carnes",
    "fruteria": "comercio frutas y verduras",
    "fruterias": "comercio frutas y verduras",
    "pescaderia": "comercio pescados y mariscos",
    "pescaderias": "comercio pescados y mariscos",
    "muebleria": "comercio muebles",
    "mueblerias": "comercio muebles",
    "zapateria": "comercio calzado zapatos",
    "zapaterias": "comercio calzado zapatos",
    "boutique": "comercio ropa prendas de vestir",
    "boutiques": "comercio ropa prendas de vestir",
    "abogado": "servicios legales juridico bufete",
    "abogados": "servicios legales juridico bufete",
    "contador": "contabilidad fiscal auditoria",
    "contadores": "contabilidad fiscal auditoria",
    "arquitecto": "servicios de arquitectura",
    "arquitectos": "servicios de arquitectura",
    "ingeniero": "servicios de ingenieria",
    "ingenieros": "servicios de ingenieria",
    "imprenta": "impresion",
    "imprentas": "impresion",
    "lavanderia": "lavanderias y tintorerias",
    "lavanderias": "lavanderias y tintorerias",
}

# Pistas semánticas del lado del catálogo SCIAN. Si el título de un nodo o camino
# cumple el patrón, se le agregan estas palabras para mejorar la recuperación.
TITLE_HINT_RULES = [
    (
        r"preparacion de alimentos|bebidas|restaurante|comida",
        "restaurante restaurantes cafeteria cafeterias cafe loncheria fonda comedor taqueria pizzeria cocina economica comida alimentos bebidas bar cantina",
    ),
    (
        r"abarrotes|ultramarinos|miscelaneas",
        "abarrotes minisuper tienda conveniencia despensa miscelanea ultramarinos",
    ),
    (
        r"farmaceutic|naturalistas",
        "farmacia farmacias botica medicamentos medicinas",
    ),
    (
        r"consultorios dentales|dental",
        "dentista dentistas odontologo odontologia dental",
    ),
    (
        r"consultorios medicos",
        "doctor doctores clinica clinicas medico medica consultorio",
    ),
    (
        r"psicologia",
        "psicologo psicologa terapia psicologia",
    ),
    (
        r"veterinari",
        "veterinaria veterinario mascotas animales perro gato",
    ),
    (
        r"belleza|peluquer|barber",
        "estetica belleza barberia salon peluqueria manicure pedicure spa",
    ),
    (
        r"ferreter|tlapaler",
        "ferreteria tlapaleria herramientas herrajes",
    ),
    (
        r"papelera|papeleria",
        "papeleria utiles escolares oficina libros revistas periodicos copias",
    ),
    (
        r"software|programacion|procesamiento de datos|diseno de sistemas",
        "software sistemas programacion desarrollo app aplicaciones informatica tecnologia",
    ),
    (
        r"autotransporte|transporte de carga|mudanzas|mensajeria|paqueteria",
        "fletes paqueteria mudanzas carga transporte logistica reparto mensajeria",
    ),
    (
        r"reparacion mecanica automotriz|automovil|camiones",
        "taller mecanico automotriz autos coche carro reparacion",
    ),
    (
        r"hotel|motel|alojamiento temporal",
        "hotel hospedaje motel posada hostal alojamiento",
    ),
    (
        r"guarderias",
        "guarderia estancia infantil kinder maternal",
    ),
    (
        r"acondicionamiento fisico|gimnasios",
        "gimnasio gym fitness entrenamiento pesas crossfit",
    ),
    (
        r"pan y otros productos de panaderia|panaderia",
        "panaderia pan pasteleria reposteria bolillo pastel",
    ),
    (
        r"tortillas de maiz|nixtamal",
        "tortilleria tortillas masa molino nixtamal",
    ),
    (
        r"carnes",
        "carniceria carnes",
    ),
    (
        r"frutas y verduras",
        "fruteria verduleria frutas verduras",
    ),
    (
        r"pescados y mariscos",
        "pescaderia marisqueria pescados mariscos",
    ),
    (
        r"muebles",
        "muebleria muebles",
    ),
    (
        r"calzado",
        "zapateria zapatos calzado tenis",
    ),
    (
        r"ropa|prendas de vestir",
        "ropa boutique vestir prendas moda",
    ),
    (
        r"servicios legales",
        "abogado abogados juridico legal despacho litigio",
    ),
    (
        r"servicios de contabilidad|contable",
        "contador contadores contabilidad fiscal auditoria despacho",
    ),
    (
        r"arquitectura|ingenieria",
        "arquitecto arquitectura ingeniero ingenieria despacho obra proyecto",
    ),
    (
        r"impresion|imprenta",
        "imprenta impresion serigrafia offset copias",
    ),
    (
        r"lavanderias|tintorerias",
        "lavanderia tintoreria planchado lavado ropa",
    ),
]

# Reglas puntuales para corregir casos de negocio muy comunes donde el término
# coloquial suele implicar una intención comercial específica.
QUERY_INTENT_RULES = [
    {
        "triggers": {"papeleria", "papelerias"},
        "positive_patterns": [
            r"comercio al por menor de articulos de papelera",
            r"papelera libros revistas y peridicos",
        ],
        "positive_boost": 0.22,
        "negative_patterns": [r"fabricacion de productos de papelera"],
        "negative_penalty": 0.18,
    },
    {
        "triggers": {"farmacia", "farmacias"},
        "positive_patterns": [
            r"productos farmacuticos y naturistas",
            r"farmaceut",
            r"medicamentos",
        ],
        "positive_boost": 0.24,
        "negative_patterns": [r"automoviles y camionetas", r"combustibles"],
        "negative_penalty": 0.15,
    },
    {
        "triggers": {"zapateria", "zapaterias"},
        "positive_patterns": [r"comercio al por menor de calzado"],
        "positive_boost": 0.26,
        "negative_patterns": [
            r"comercio al por mayor de calzado",
            r"fabricacion de calzado",
            r"reparacion de calzado",
        ],
        "negative_penalty": 0.12,
    },
    {
        "triggers": {"muebleria", "mueblerias"},
        "positive_patterns": [r"comercio al por menor de muebles"],
        "positive_boost": 0.24,
        "negative_patterns": [r"fabricacion de muebles"],
        "negative_penalty": 0.12,
    },
    {
        "triggers": {"boutique", "boutiques"},
        "positive_patterns": [
            r"comercio al por menor de ropa",
            r"bisuteria y accesorios de vestir",
        ],
        "positive_boost": 0.24,
        "negative_patterns": [
            r"fabricacion de prendas de vestir",
            r"confeccion de prendas de vestir",
        ],
        "negative_penalty": 0.14,
    },
    {
        "triggers": {"dentista", "dentistas", "odontologo", "odontologos"},
        "positive_patterns": [r"consultorios dentales"],
        "positive_boost": 0.2,
        "negative_patterns": [r"material desechable de uso mdico dental"],
        "negative_penalty": 0.12,
    },
    {
        "triggers": {"abarrotes"},
        "positive_patterns": [r"tiendas de abarrotes ultramarinos y miscelneas"],
        "positive_boost": 0.18,
        "negative_patterns": [r"comercio al por mayor de abarrotes"],
        "negative_penalty": 0.06,
    },

    {
        "triggers": {"abogado", "abogados"},
        "positive_patterns": [r"bufetes jurdicos", r"servicios legales"],
        "positive_boost": 0.22,
        "negative_patterns": [r"apoyo para efectuar trmites legales"],
        "negative_penalty": 0.1,
    },
    {
        "triggers": {"gimnasio", "gimnasios"},
        "positive_patterns": [r"acondicionamiento fsico", r"clubes deportivos"],
        "positive_boost": 0.18,
        "negative_patterns": [],
        "negative_penalty": 0.0,
    },
]
