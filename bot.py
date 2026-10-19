"""
Xonadon+ Telegram Bot (@xonadon_plus_bot)
Avtomatlashtirilgan gaz baloni tarqatish, SMS OTP orqali fuqaroni tasdiqlash,
ko'chalar bo'yicha aniq filtrlangan xabarnomalar xizmati.
"""

import json
import os
import sys
import db_manager
db_manager.init_db()
import time
import urllib.request
import urllib.parse
import threading
import socket
import re
import html
from http.server import HTTPServer, BaseHTTPRequestHandler

TOKEN = "8459389414:AAGovsyUvFp4RXgKg47X_sEwRnHefcuOXXI"
API_URL = f"https://api.telegram.org/bot{TOKEN}"
DB_FILE = os.path.join(os.path.dirname(__file__), "bot_subscribers.json")
HTTP_PORT = int(os.environ.get("PORT", 3001))
LOCK_PORT = int(os.environ.get("LOCK_PORT", 3005))

# ========================================================
# 0. SINGLE-INSTANCE LOCK (TAKRORIY BOT ISHGA TUSHISHINI TO'XTATISH)
# ========================================================
_lock_socket = None

def acquire_instance_lock():
    global _lock_socket
    # Cloud environments manage single containers automatically
    if os.environ.get("PORT") or os.environ.get("RENDER") or os.environ.get("RAILWAY_STATIC_URL"):
        return True
    _lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        _lock_socket.bind(("127.0.0.1", LOCK_PORT))
        _lock_socket.listen(1)
        return True
    except OSError:
        print(f"[BOT DIQQAT] Botning boshqa nusxasi allaqachon ishlamoqda (Port {LOCK_PORT} band).")
        print("[BOT] Takroriy xabarlarning oldini olish uchun ushbu nusxa to‘xtatildi.")
        sys.exit(0)

# ========================================================
# 1. MANZILLAR BAZASI (WEB ILOVA BILAN 100% BIR XIL)
# ========================================================
ADDRESS_DB = {
    "qoraqalpogiston": {
        "name": "Qoraqalpog‘iston Respublikasi",
        "districts": {
            "nukus_sh": {
                "name": "Nukus shahri",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Markaz» MFY",
                        "streets": {
                            "markaziy_k": "A. Dosnazarov ko‘chasi"
                        }
                    }
                }
            },
            "amudaryo": {
                "name": "Amudaryo tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Mang‘it» MFY",
                        "streets": {
                            "markaziy_k": "Amudaryo ko‘chasi"
                        }
                    }
                }
            },
            "beruniy": {
                "name": "Beruniy tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Al-Beruniy» MFY",
                        "streets": {
                            "markaziy_k": "Jayhun ko‘chasi"
                        }
                    }
                }
            },
            "chimboy": {
                "name": "Chimboy tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Chimboy» MFY",
                        "streets": {
                            "markaziy_k": "G‘o‘ravon ko‘chasi"
                        }
                    }
                }
            },
            "ellikqala": {
                "name": "Ellikqala tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Bo‘ston» MFY",
                        "streets": {
                            "markaziy_k": "Paxtakor ko‘chasi"
                        }
                    }
                }
            },
            "kegeyli": {
                "name": "Kegeyli tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Kegeyli» MFY",
                        "streets": {
                            "markaziy_k": "Nurli yo‘l ko‘chasi"
                        }
                    }
                }
            },
            "moynoq": {
                "name": "Mo‘ynoq tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Orol» MFY",
                        "streets": {
                            "markaziy_k": "Mayoq ko‘chasi"
                        }
                    }
                }
            },
            "nukus_t": {
                "name": "Nukus tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Oqmang‘it» MFY",
                        "streets": {
                            "markaziy_k": "Dehqon ko‘chasi"
                        }
                    }
                }
            },
            "qanlikol": {
                "name": "Qanliko‘l tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Qanliko‘l» MFY",
                        "streets": {
                            "markaziy_k": "Mustaqillik ko‘chasi"
                        }
                    }
                }
            },
            "qongirot": {
                "name": "Qo‘ng‘irot tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Qo‘ng‘irot» MFY",
                        "streets": {
                            "markaziy_k": "Temiryo‘l ko‘chasi"
                        }
                    }
                }
            },
            "qoraozak": {
                "name": "Qorao‘zak tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Qorao‘zak» MFY",
                        "streets": {
                            "markaziy_k": "Obod zamin ko‘chasi"
                        }
                    }
                }
            },
            "shumanay": {
                "name": "Shumanay tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Shumanay» MFY",
                        "streets": {
                            "markaziy_k": "Yoshlik ko‘chasi"
                        }
                    }
                }
            },
            "taxtakopir": {
                "name": "Taxtako‘pir tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Taxtako‘pir» MFY",
                        "streets": {
                            "markaziy_k": "Shodlik ko‘chasi"
                        }
                    }
                }
            },
            "tortkol": {
                "name": "To‘rtko‘l tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«To‘rtko‘l» MFY",
                        "streets": {
                            "markaziy_k": "Ibn Sino ko‘chasi"
                        }
                    }
                }
            },
            "xojayli": {
                "name": "Xo‘jayli tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Xo‘jayli» MFY",
                        "streets": {
                            "markaziy_k": "Samarqand ko‘chasi"
                        }
                    }
                }
            }
        }
    },
    "andijon": {
        "name": "Andijon viloyati",
        "districts": {
            "andijon_sh": {
                "name": "Andijon shahri",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Bobur» MFY",
                        "streets": {
                            "markaziy_k": "Fitrat ko‘chasi"
                        }
                    }
                }
            },
            "xonobod_sh": {
                "name": "Xonobod shahri",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Xonobod» MFY",
                        "streets": {
                            "markaziy_k": "Farg‘ona ko‘chasi"
                        }
                    }
                }
            },
            "andijon_t": {
                "name": "Andijon tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Kuyganyor» MFY",
                        "streets": {
                            "markaziy_k": "Zahiriddin Bobur ko‘chasi"
                        }
                    }
                }
            },
            "asaka": {
                "name": "Asaka tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Asaka» MFY",
                        "streets": {
                            "markaziy_k": "Avtomobilchilar ko‘chasi"
                        }
                    }
                }
            },
            "baliqchi": {
                "name": "Baliqchi tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Baliqchi» MFY",
                        "streets": {
                            "markaziy_k": "Chinor ko‘chasi"
                        }
                    }
                }
            },
            "boston": {
                "name": "Bo‘ston tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Bo‘z» MFY",
                        "streets": {
                            "markaziy_k": "Navbahor ko‘chasi"
                        }
                    }
                }
            },
            "buloqboshi": {
                "name": "Buloqboshi tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Buloqboshi» MFY",
                        "streets": {
                            "markaziy_k": "Shifokorlar ko‘chasi"
                        }
                    }
                }
            },
            "izboskan": {
                "name": "Izboskan tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Poytug‘» MFY",
                        "streets": {
                            "markaziy_k": "Mustaqillik ko‘chasi"
                        }
                    }
                }
            },
            "jalaquduq": {
                "name": "Jalaquduq tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Oxunboboyev» MFY",
                        "streets": {
                            "markaziy_k": "Do‘stlik ko‘chasi"
                        }
                    }
                }
            },
            "xojaobod": {
                "name": "Xo‘jaobod tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Xo‘jaobod» MFY",
                        "streets": {
                            "markaziy_k": "Guliston ko‘chasi"
                        }
                    }
                }
            },
            "qorgontepa": {
                "name": "Qo‘rg‘ontepa tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Qorasuv» MFY",
                        "streets": {
                            "markaziy_k": "Ipak yo‘li ko‘chasi"
                        }
                    }
                }
            },
            "marhamat": {
                "name": "Marhamat tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Marhamat» MFY",
                        "streets": {
                            "markaziy_k": "Bog‘ishamol ko‘chasi"
                        }
                    }
                }
            },
            "oltinkol": {
                "name": "Oltinko‘l tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Oltinko‘l» MFY",
                        "streets": {
                            "markaziy_k": "Oltin vodiy ko‘chasi"
                        }
                    }
                }
            },
            "paxtaobod": {
                "name": "Paxtaobod tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Paxtaobod» MFY",
                        "streets": {
                            "markaziy_k": "Paxtakor ko‘chasi"
                        }
                    }
                }
            },
            "ulugnor": {
                "name": "Ulug‘nor tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Oq oltin» MFY",
                        "streets": {
                            "markaziy_k": "Zarbdor ko‘chasi"
                        }
                    }
                }
            },
            "shahrixon": {
                "name": "Shahrixon tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Shahrixon» MFY",
                        "streets": {
                            "markaziy_k": "Hunarmandlar ko‘chasi"
                        }
                    }
                }
            }
        }
    },
    "buxoro": {
        "name": "Buxoro viloyati",
        "districts": {
            "buxoro_sh": {
                "name": "Buxoro shahri",
                "mfys": {
                    "somoniylar": {
                        "name": "«Somoniylar» MFY",
                        "streets": {
                            "naqshband": "Bahouddin Naqshband ko‘chasi"
                        }
                    }
                }
            },
            "kogon_sh": {
                "name": "Kogon shahri",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Temiryo‘lchi» MFY",
                        "streets": {
                            "markaziy_k": "Buxoro ko‘chasi"
                        }
                    }
                }
            },
            "buxoro_t": {
                "name": "Buxoro tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Galaosiyo» MFY",
                        "streets": {
                            "markaziy_k": "Ibn Sino ko‘chasi"
                        }
                    }
                }
            },
            "vobkent": {
                "name": "Vobkent tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Vobkent» MFY",
                        "streets": {
                            "markaziy_k": "Minorayi Kalon ko‘chasi"
                        }
                    }
                }
            },
            "gijduvon": {
                "name": "G‘ijduvon tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Kulollar» MFY",
                        "streets": {
                            "markaziy_k": "Kulolchilik ko‘chasi"
                        }
                    }
                }
            },
            "jondor": {
                "name": "Jondor tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Jondor» MFY",
                        "streets": {
                            "markaziy_k": "Zarafshon ko‘chasi"
                        }
                    }
                }
            },
            "kogon_t": {
                "name": "Kogon tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Sarayon» MFY",
                        "streets": {
                            "markaziy_k": "Yoshlik ko‘chasi"
                        }
                    }
                }
            },
            "qorakol": {
                "name": "Qorako‘l tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Qorako‘l» MFY",
                        "streets": {
                            "markaziy_k": "Ulug‘bek ko‘chasi"
                        }
                    }
                }
            },
            "qorovulbozor": {
                "name": "Qorovulbozor tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Neftchilar» MFY",
                        "streets": {
                            "markaziy_k": "Nurli kelajak ko‘chasi"
                        }
                    }
                }
            },
            "olot": {
                "name": "Olot tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Olot» MFY",
                        "streets": {
                            "markaziy_k": "Mustaqillik ko‘chasi"
                        }
                    }
                }
            },
            "peshku": {
                "name": "Peshku tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Yangibozor» MFY",
                        "streets": {
                            "markaziy_k": "Navro‘z ko‘chasi"
                        }
                    }
                }
            },
            "romitan": {
                "name": "Romitan tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Romitan» MFY",
                        "streets": {
                            "markaziy_k": "Afrosiyob ko‘chasi"
                        }
                    }
                }
            },
            "shofirkon": {
                "name": "Shofirkon tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Shofirkon» MFY",
                        "streets": {
                            "markaziy_k": "Bog‘i Eram ko‘chasi"
                        }
                    }
                }
            }
        }
    },
    "jizzax": {
        "name": "Jizzax viloyati",
        "districts": {
            "jizzax_sh": {
                "name": "Jizzax shahri",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Sayiljoyi» MFY",
                        "streets": {
                            "markaziy_k": "Sharof Rashidov shoh ko‘chasi"
                        }
                    }
                }
            },
            "arnasoy": {
                "name": "Arnasoy tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«G‘oliblar» MFY",
                        "streets": {
                            "markaziy_k": "Arnasoy ko‘chasi"
                        }
                    }
                }
            },
            "baxmal": {
                "name": "Baxmal tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«O‘smat» MFY",
                        "streets": {
                            "markaziy_k": "Tog‘ bag‘ri ko‘chasi"
                        }
                    }
                }
            },
            "dostlik": {
                "name": "Do‘stlik tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Do‘stlik» MFY",
                        "streets": {
                            "markaziy_k": "Navro‘z ko‘chasi"
                        }
                    }
                }
            },
            "forish": {
                "name": "Forish tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Bog‘don» MFY",
                        "streets": {
                            "markaziy_k": "Nurli quyosh ko‘chasi"
                        }
                    }
                }
            },
            "gallaorol": {
                "name": "G‘allaorol tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«G‘allaorol» MFY",
                        "streets": {
                            "markaziy_k": "G‘allakor ko‘chasi"
                        }
                    }
                }
            },
            "sharof_rashidov": {
                "name": "Sharof Rashidov tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Uchtepa» MFY",
                        "streets": {
                            "markaziy_k": "Istiqlol ko‘chasi"
                        }
                    }
                }
            },
            "mirzachol": {
                "name": "Mirzacho‘l tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Gagarin» MFY",
                        "streets": {
                            "markaziy_k": "Mirzacho‘l ko‘chasi"
                        }
                    }
                }
            },
            "paxtakor": {
                "name": "Paxtakor tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Paxtakor» MFY",
                        "streets": {
                            "markaziy_k": "Paxtazor ko‘chasi"
                        }
                    }
                }
            },
            "yangiobod": {
                "name": "Yangiobod tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Balandchaqir» MFY",
                        "streets": {
                            "markaziy_k": "Zomin yo‘li ko‘chasi"
                        }
                    }
                }
            },
            "zomin": {
                "name": "Zomin tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Zomin» MFY",
                        "streets": {
                            "markaziy_k": "Archa ko‘chasi"
                        }
                    }
                }
            },
            "zafarobod": {
                "name": "Zafarobod tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Zafarobod» MFY",
                        "streets": {
                            "markaziy_k": "Yangi zamin ko‘chasi"
                        }
                    }
                }
            },
            "zarbdor": {
                "name": "Zarbdor tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Zarbdor» MFY",
                        "streets": {
                            "markaziy_k": "Shodlik ko‘chasi"
                        }
                    }
                }
            }
        }
    },
    "qashqadaryo": {
        "name": "Qashqadaryo viloyati",
        "districts": {
            "nishon": {
                "name": "Nishon tumani",
                "mfys": {
                    "koksoy": {
                        "name": "«Ko‘ksoy» MFY",
                        "streets": {
                            "koksoy_markaziy": "Ko‘ksoy markaziy ko‘chasi",
                            "maktab_k": "Maktab ko‘chasi (28-maktab)",
                            "paxtakor_k": "Paxtakor ko‘chasi",
                            "yoshlik_k": "Yoshlik ko‘chasi",
                            "nurafshon_k": "Nurafshon ko‘chasi",
                            "bogiston_k": "Bog‘iston ko‘chasi",
                            "ziyokorlar_k": "Ziyokorlar ko‘chasi",
                            "guliston_k": "Guliston ko‘chasi",
                            "navbahor_k": "Navbahor ko‘chasi",
                            "shifokorlar_k": "Shifokorlar ko‘chasi (QVP)"
                        }
                    },
                    "yangi_nishon": {
                        "name": "«Yangi Nishon» MFY",
                        "streets": {
                            "istiqlol": "Istiqlol ko‘chasi",
                            "mustaqillik": "Mustaqillik ko‘chasi",
                            "temiryol": "Temiryo‘lchilar ko‘chasi"
                        }
                    },
                    "paxtazor": {
                        "name": "«Paxtazor» MFY",
                        "streets": {
                            "paxtakor": "Paxtakor ko‘chasi",
                            "dostlik": "Do‘stlik ko‘chasi",
                            "yoshlik": "Yoshlik ko‘chasi"
                        }
                    },
                    "shirin": {
                        "name": "«Shirin» MFY",
                        "streets": {
                            "shirin_k": "Shirinobod ko‘chasi",
                            "guliston": "Guliston ko‘chasi"
                        }
                    },
                    "balx": {
                        "name": "«Balx» MFY",
                        "streets": {
                            "balx_k": "Balx ko‘chasi"
                        }
                    },
                    "oydin": {
                        "name": "«Oydin» MFY",
                        "streets": {
                            "oydin_k": "Oydin hayot ko‘chasi"
                        }
                    }
                }
            },
            "qarshi_sh": {
                "name": "Qarshi shahri",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Nasaf» MFY",
                        "streets": {
                            "markaziy_k": "Mustaqillik shoh ko‘chasi"
                        }
                    }
                }
            },
            "shahrisabz_sh": {
                "name": "Shahrisabz shahri",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Koba» MFY",
                        "streets": {
                            "markaziy_k": "Ipak Yo‘li ko‘chasi"
                        }
                    }
                }
            },
            "qarshi_t": {
                "name": "Qarshi tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Beshkent» MFY",
                        "streets": {
                            "markaziy_k": "Nasaf ko‘chasi"
                        }
                    }
                }
            },
            "shahrisabz_t": {
                "name": "Shahrisabz tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Oqsaroy» MFY",
                        "streets": {
                            "markaziy_k": "Amir Temur ko‘chasi"
                        }
                    }
                }
            },
            "kasbi": {
                "name": "Kasbi tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Mug‘lon» MFY",
                        "streets": {
                            "markaziy_k": "Kasbi markaziy ko‘chasi"
                        }
                    }
                }
            },
            "koson": {
                "name": "Koson tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Koson» MFY",
                        "streets": {
                            "markaziy_k": "Istirohat ko‘chasi"
                        }
                    }
                }
            },
            "kitob": {
                "name": "Kitob tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Kitob» MFY",
                        "streets": {
                            "markaziy_k": "Tog‘oldi ko‘chasi"
                        }
                    }
                }
            },
            "guzor": {
                "name": "G‘uzor tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Sho‘rtan» MFY",
                        "streets": {
                            "markaziy_k": "Gazchilar ko‘chasi"
                        }
                    }
                }
            },
            "chiroqchi": {
                "name": "Chiroqchi tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Chiroqchi» MFY",
                        "streets": {
                            "markaziy_k": "Obod ko‘chasi"
                        }
                    }
                }
            },
            "dehqonobod": {
                "name": "Dehqonobod tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Qorashina» MFY",
                        "streets": {
                            "markaziy_k": "Konchilar ko‘chasi"
                        }
                    }
                }
            },
            "qamashi": {
                "name": "Qamashi tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Qamashi» MFY",
                        "streets": {
                            "markaziy_k": "Langar ko‘chasi"
                        }
                    }
                }
            },
            "mirishkor": {
                "name": "Mirishkor tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Yangi Mirishkor» MFY",
                        "streets": {
                            "markaziy_k": "Jayhun ko‘chasi"
                        }
                    }
                }
            },
            "muborak": {
                "name": "Muborak tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Muborak» MFY",
                        "streets": {
                            "markaziy_k": "Mash’al ko‘chasi"
                        }
                    }
                }
            },
            "yakkabog": {
                "name": "Yakkabog‘ tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Yakkabog‘» MFY",
                        "streets": {
                            "markaziy_k": "Bog‘zor ko‘chasi"
                        }
                    }
                }
            },
            "kokdala": {
                "name": "Ko‘kdala tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Yettitom» MFY",
                        "streets": {
                            "markaziy_k": "Ko‘kdala ko‘chasi"
                        }
                    }
                }
            }
        }
    },
    "navoiy": {
        "name": "Navoiy viloyati",
        "districts": {
            "navoiy_sh": {
                "name": "Navoiy shahri",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Kimyogar» MFY",
                        "streets": {
                            "markaziy_k": "G‘alaba shoh ko‘chasi"
                        }
                    }
                }
            },
            "zarafshon_sh": {
                "name": "Zarafshon shahri",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Oltin vodiy» MFY",
                        "streets": {
                            "markaziy_k": "Konchilar ko‘chasi"
                        }
                    }
                }
            },
            "karmana": {
                "name": "Karmana tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Qosim Shayx» MFY",
                        "streets": {
                            "markaziy_k": "Alisher Navoiy ko‘chasi"
                        }
                    }
                }
            },
            "konimex": {
                "name": "Konimex tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Konimex» MFY",
                        "streets": {
                            "markaziy_k": "Do‘stlik ko‘chasi"
                        }
                    }
                }
            },
            "qiziltepa": {
                "name": "Qiziltepa tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Qiziltepa» MFY",
                        "streets": {
                            "markaziy_k": "Toshkent ko‘chasi"
                        }
                    }
                }
            },
            "xatirchi": {
                "name": "Xatirchi tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Yangi rabot» MFY",
                        "streets": {
                            "markaziy_k": "Zarafshon ko‘chasi"
                        }
                    }
                }
            },
            "navbahor": {
                "name": "Navbahor tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Beshrabot» MFY",
                        "streets": {
                            "markaziy_k": "Paxtakor ko‘chasi"
                        }
                    }
                }
            },
            "nurota": {
                "name": "Nurota tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Chashma» MFY",
                        "streets": {
                            "markaziy_k": "Nur ko‘chasi"
                        }
                    }
                }
            },
            "tomdi": {
                "name": "Tomdi tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Tomdibuloq» MFY",
                        "streets": {
                            "markaziy_k": "Cho‘l havosi ko‘chasi"
                        }
                    }
                }
            },
            "uchquduq": {
                "name": "Uchquduq tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Uchquduq» MFY",
                        "streets": {
                            "markaziy_k": "Geologlar ko‘chasi"
                        }
                    }
                }
            }
        }
    },
    "namangan": {
        "name": "Namangan viloyati",
        "districts": {
            "namangan_sh": {
                "name": "Namangan shahri",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Bobur bog‘i» MFY",
                        "streets": {
                            "markaziy_k": "Uychi ko‘chasi"
                        }
                    }
                }
            },
            "chortoq": {
                "name": "Chortoq tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Chortoq» MFY",
                        "streets": {
                            "markaziy_k": "Sihatgoh ko‘chasi"
                        }
                    }
                }
            },
            "chust": {
                "name": "Chust tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Pichoqchilar» MFY",
                        "streets": {
                            "markaziy_k": "Chustiy ko‘chasi"
                        }
                    }
                }
            },
            "kosonsoy": {
                "name": "Kosonsoy tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Kosonsoy» MFY",
                        "streets": {
                            "markaziy_k": "Gulbog‘ ko‘chasi"
                        }
                    }
                }
            },
            "mingbuloq": {
                "name": "Mingbuloq tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Jumabozor» MFY",
                        "streets": {
                            "markaziy_k": "Paxtakor ko‘chasi"
                        }
                    }
                }
            },
            "namangan_t": {
                "name": "Namangan tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Toshbuloq» MFY",
                        "streets": {
                            "markaziy_k": "Mustaqillik ko‘chasi"
                        }
                    }
                }
            },
            "norin": {
                "name": "Norin tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Haqqulobod» MFY",
                        "streets": {
                            "markaziy_k": "Norin daryo ko‘chasi"
                        }
                    }
                }
            },
            "pop": {
                "name": "Pop tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Pop» MFY",
                        "streets": {
                            "markaziy_k": "Qamchiq ko‘chasi"
                        }
                    }
                }
            },
            "toraqorgon": {
                "name": "To‘raqo‘rg‘on tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Ishoqxon Ibrat» MFY",
                        "streets": {
                            "markaziy_k": "Ibrat ko‘chasi"
                        }
                    }
                }
            },
            "uchqorgon": {
                "name": "Uchqo‘rg‘on tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Uchqo‘rg‘on» MFY",
                        "streets": {
                            "markaziy_k": "Norinbo‘yi ko‘chasi"
                        }
                    }
                }
            },
            "uychi": {
                "name": "Uychi tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Uychi» MFY",
                        "streets": {
                            "markaziy_k": "Yangi hayot ko‘chasi"
                        }
                    }
                }
            },
            "yangiqorgon": {
                "name": "Yangiqo‘rg‘on tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Yangiqo‘rg‘on» MFY",
                        "streets": {
                            "markaziy_k": "Olmazor ko‘chasi"
                        }
                    }
                }
            },
            "davlatobod": {
                "name": "Davlatobod tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Yuksalish» MFY",
                        "streets": {
                            "markaziy_k": "Afsonalar vodiysi ko‘chasi"
                        }
                    }
                }
            },
            "yangi_namangan": {
                "name": "Yangi Namangan tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Mehrigiyo» MFY",
                        "streets": {
                            "markaziy_k": "Yangi O‘zbekiston ko‘chasi"
                        }
                    }
                }
            }
        }
    },
    "samarqand": {
        "name": "Samarqand viloyati",
        "districts": {
            "pastdargom": {
                "name": "Pastdarg‘om tumani",
                "mfys": {
                    "olti_qahramon": {
                        "name": "«Olti qahramon» MFY",
                        "streets": {
                            "bogishamol": "Bog‘ishamol ko‘chasi",
                            "gulzor": "Gulzor ko‘chasi",
                            "navbahor": "Navbahor ko‘chasi",
                            "yoshlik_p": "Yoshlik ko‘chasi"
                        }
                    },
                    "charxin": {
                        "name": "«Charxin» MFY",
                        "streets": {
                            "ziyo": "Ziyo ko‘chasi",
                            "mustaqillik_ch": "Mustaqillik ko‘chasi"
                        }
                    },
                    "chimboy": {
                        "name": "«Chimboy» MFY",
                        "streets": {
                            "paxtakor_ch": "Paxtakor ko‘chasi"
                        }
                    }
                }
            },
            "samarqand_sh": {
                "name": "Samarqand shahri",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Registon» MFY",
                        "streets": {
                            "markaziy_k": "Dagbit ko‘chasi"
                        }
                    }
                }
            },
            "kattaqorgon_sh": {
                "name": "Kattaqo‘rg‘on shahri",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Kattaqo‘rg‘on» MFY",
                        "streets": {
                            "markaziy_k": "Amir Temur ko‘chasi"
                        }
                    }
                }
            },
            "urgut": {
                "name": "Urgut tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Chorchinor» MFY",
                        "streets": {
                            "markaziy_k": "Katta Chinor ko‘chasi"
                        }
                    }
                }
            },
            "toyloq": {
                "name": "Toyloq tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Toyloq» MFY",
                        "streets": {
                            "markaziy_k": "Bog‘ishamol ko‘chasi"
                        }
                    }
                }
            },
            "kattaqorgon_t": {
                "name": "Kattaqo‘rg‘on tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Payshanba» MFY",
                        "streets": {
                            "markaziy_k": "Alisher Navoiy ko‘chasi"
                        }
                    }
                }
            },
            "bulungur": {
                "name": "Bulung‘ur tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Bulung‘ur» MFY",
                        "streets": {
                            "markaziy_k": "Dehqonobod ko‘chasi"
                        }
                    }
                }
            },
            "ishtixon": {
                "name": "Ishtixon tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Ishtixon» MFY",
                        "streets": {
                            "markaziy_k": "Mustaqillik ko‘chasi"
                        }
                    }
                }
            },
            "jomboy": {
                "name": "Jomboy tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Jomboy» MFY",
                        "streets": {
                            "markaziy_k": "Zarafshon ko‘chasi"
                        }
                    }
                }
            },
            "narpay": {
                "name": "Narpay tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Oqtosh» MFY",
                        "streets": {
                            "markaziy_k": "Ipak yo‘li ko‘chasi"
                        }
                    }
                }
            },
            "nurobod": {
                "name": "Nurobod tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Nurbuloq» MFY",
                        "streets": {
                            "markaziy_k": "Nurli zamin ko‘chasi"
                        }
                    }
                }
            },
            "oqdaryo": {
                "name": "Oqdaryo tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Loyish» MFY",
                        "streets": {
                            "markaziy_k": "Oqdaryo ko‘chasi"
                        }
                    }
                }
            },
            "paxtachi": {
                "name": "Paxtachi tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Ziyovuddin» MFY",
                        "streets": {
                            "markaziy_k": "Paxtakor ko‘chasi"
                        }
                    }
                }
            },
            "payariq": {
                "name": "Payariq tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Payariq» MFY",
                        "streets": {
                            "markaziy_k": "Imom Buxoriy ko‘chasi"
                        }
                    }
                }
            },
            "qoshrabot": {
                "name": "Qo‘shrabot tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Qo‘shrabot» MFY",
                        "streets": {
                            "markaziy_k": "Tog‘oldi ko‘chasi"
                        }
                    }
                }
            },
            "samarqand_t": {
                "name": "Samarqand tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Konigil» MFY",
                        "streets": {
                            "markaziy_k": "Ipak qog‘ozi ko‘chasi"
                        }
                    }
                }
            }
        }
    },
    "surxondaryo": {
        "name": "Surxondaryo viloyati",
        "districts": {
            "termiz_sh": {
                "name": "Termiz shahri",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Al-Hakim at-Termiziy» MFY",
                        "streets": {
                            "markaziy_k": "At-Termiziy shoh ko‘chasi"
                        }
                    }
                }
            },
            "angor": {
                "name": "Angor tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Angor» MFY",
                        "streets": {
                            "markaziy_k": "Surxon ko‘chasi"
                        }
                    }
                }
            },
            "bandixon": {
                "name": "Bandixon tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Bandixon» MFY",
                        "streets": {
                            "markaziy_k": "Obod zamin ko‘chasi"
                        }
                    }
                }
            },
            "boysun": {
                "name": "Boysun tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Boysun» MFY",
                        "streets": {
                            "markaziy_k": "Alpomish ko‘chasi"
                        }
                    }
                }
            },
            "denov": {
                "name": "Denov tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Denov» MFY",
                        "streets": {
                            "markaziy_k": "Shaxriston ko‘chasi"
                        }
                    }
                }
            },
            "jarqorgon": {
                "name": "Jarqo‘rg‘on tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Minor» MFY",
                        "streets": {
                            "markaziy_k": "Minorai Kalon ko‘chasi"
                        }
                    }
                }
            },
            "muzrabot": {
                "name": "Muzrabot tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Xalqobod» MFY",
                        "streets": {
                            "markaziy_k": "Zarbdor ko‘chasi"
                        }
                    }
                }
            },
            "oltinsoy": {
                "name": "Oltinsoy tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Qorabuloq» MFY",
                        "streets": {
                            "markaziy_k": "Oltin vodiy ko‘chasi"
                        }
                    }
                }
            },
            "qiziriq": {
                "name": "Qiziriq tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Sariq» MFY",
                        "streets": {
                            "markaziy_k": "Istiqlol ko‘chasi"
                        }
                    }
                }
            },
            "qumqorgon": {
                "name": "Qumqo‘rg‘on tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Qumqo‘rg‘on» MFY",
                        "streets": {
                            "markaziy_k": "Mustaqillik ko‘chasi"
                        }
                    }
                }
            },
            "sariosiyo": {
                "name": "Sariosiyo tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Sariosiyo» MFY",
                        "streets": {
                            "markaziy_k": "To‘polong ko‘chasi"
                        }
                    }
                }
            },
            "sherobod": {
                "name": "Sherobod tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Sherobod» MFY",
                        "streets": {
                            "markaziy_k": "Anorzor ko‘chasi"
                        }
                    }
                }
            },
            "shorchi": {
                "name": "Sho‘rchi tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Sho‘rchi» MFY",
                        "streets": {
                            "markaziy_k": "Dehqon ko‘chasi"
                        }
                    }
                }
            },
            "termiz_t": {
                "name": "Termiz tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Uchqizil» MFY",
                        "streets": {
                            "markaziy_k": "Amudaryo bo‘yi ko‘chasi"
                        }
                    }
                }
            },
            "uzun": {
                "name": "Uzun tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Uzun» MFY",
                        "streets": {
                            "markaziy_k": "Bobotog‘ ko‘chasi"
                        }
                    }
                }
            }
        }
    },
    "sirdaryo": {
        "name": "Sirdaryo viloyati",
        "districts": {
            "guliston_sh": {
                "name": "Guliston shahri",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Bo‘ston» MFY",
                        "streets": {
                            "markaziy_k": "Mustaqillik shoh ko‘chasi"
                        }
                    }
                }
            },
            "shirin_sh": {
                "name": "Shirin shahri",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Farhod» MFY",
                        "streets": {
                            "markaziy_k": "Energetiklar ko‘chasi"
                        }
                    }
                }
            },
            "yangiyer_sh": {
                "name": "Yangiyer shahri",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Shukrona» MFY",
                        "streets": {
                            "markaziy_k": "Bunyodkor ko‘chasi"
                        }
                    }
                }
            },
            "oqoltin": {
                "name": "Oqoltin tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Sardoba» MFY",
                        "streets": {
                            "markaziy_k": "Oq oltin ko‘chasi"
                        }
                    }
                }
            },
            "boyovut": {
                "name": "Boyovut tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Boyovut» MFY",
                        "streets": {
                            "markaziy_k": "Navbahor ko‘chasi"
                        }
                    }
                }
            },
            "guliston_t": {
                "name": "Guliston tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Dehqonobod» MFY",
                        "streets": {
                            "markaziy_k": "Do‘stlik ko‘chasi"
                        }
                    }
                }
            },
            "xovos": {
                "name": "Xovos tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Xovos» MFY",
                        "streets": {
                            "markaziy_k": "Temiryo‘lchilar ko‘chasi"
                        }
                    }
                }
            },
            "mirzaobod": {
                "name": "Mirzaobod tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Navro‘z» MFY",
                        "streets": {
                            "markaziy_k": "Mirzacho‘l ko‘chasi"
                        }
                    }
                }
            },
            "sayxunobod": {
                "name": "Sayxunobod tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Sayxun» MFY",
                        "streets": {
                            "markaziy_k": "Sirdaryo ko‘chasi"
                        }
                    }
                }
            },
            "sardoba": {
                "name": "Sardoba tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Paxtaobod» MFY",
                        "streets": {
                            "markaziy_k": "Zarbdor ko‘chasi"
                        }
                    }
                }
            },
            "sirdaryo_t": {
                "name": "Sirdaryo tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Baxt» MFY",
                        "streets": {
                            "markaziy_k": "Ipak yo‘li ko‘chasi"
                        }
                    }
                }
            }
        }
    },
    "toshkent_vil": {
        "name": "Toshkent viloyati",
        "districts": {
            "chirchiq_sh": {
                "name": "Chirchiq shahri",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Kimyogar» MFY",
                        "streets": {
                            "markaziy_k": "A. Navoiy shoh ko‘chasi"
                        }
                    }
                }
            },
            "angren_sh": {
                "name": "Angren shahri",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Konchi» MFY",
                        "streets": {
                            "markaziy_k": "Mustaqillik ko‘chasi"
                        }
                    }
                }
            },
            "olmaliq_sh": {
                "name": "Olmaliq shahri",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Metallurg» MFY",
                        "streets": {
                            "markaziy_k": "Metallurglar ko‘chasi"
                        }
                    }
                }
            },
            "bekobod_sh": {
                "name": "Bekobod shahri",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Po‘lat» MFY",
                        "streets": {
                            "markaziy_k": "Sirg‘ali ko‘chasi"
                        }
                    }
                }
            },
            "nurafshon_sh": {
                "name": "Nurafshon shahri",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Nurafshon» MFY",
                        "streets": {
                            "markaziy_k": "Toshkent yo‘li ko‘chasi"
                        }
                    }
                }
            },
            "yangiyol_sh": {
                "name": "Yangiyo‘l shahri",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Yangiyo‘l» MFY",
                        "streets": {
                            "markaziy_k": "Samarqand ko‘chasi"
                        }
                    }
                }
            },
            "bekobod_t": {
                "name": "Bekobod tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Zafar» MFY",
                        "streets": {
                            "markaziy_k": "Dehqonobod ko‘chasi"
                        }
                    }
                }
            },
            "bostonliq": {
                "name": "Bo‘stonliq tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«G‘azalkent» MFY",
                        "streets": {
                            "markaziy_k": "Chorvoq ko‘chasi"
                        }
                    }
                }
            },
            "boka": {
                "name": "Bo‘ka tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Bo‘ka» MFY",
                        "streets": {
                            "markaziy_k": "Istiqlol ko‘chasi"
                        }
                    }
                }
            },
            "chinoz": {
                "name": "Chinoz tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Chinoz» MFY",
                        "streets": {
                            "markaziy_k": "Sirdaryo bo‘yi ko‘chasi"
                        }
                    }
                }
            },
            "qibray": {
                "name": "Qibray tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Qibray» MFY",
                        "streets": {
                            "markaziy_k": "Bog‘ishamol ko‘chasi"
                        }
                    }
                }
            },
            "parkent": {
                "name": "Parkent tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Parkent» MFY",
                        "streets": {
                            "markaziy_k": "Quyosh ko‘chasi"
                        }
                    }
                }
            },
            "piskent": {
                "name": "Piskent tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Piskent» MFY",
                        "streets": {
                            "markaziy_k": "Obod yurt ko‘chasi"
                        }
                    }
                }
            },
            "quyi_chirchiq": {
                "name": "Quyi Chirchiq tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Do‘stobod» MFY",
                        "streets": {
                            "markaziy_k": "Chirchiq bo‘yi ko‘chasi"
                        }
                    }
                }
            },
            "orta_chirchiq": {
                "name": "O‘rta Chirchiq tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«To‘ytepa» MFY",
                        "streets": {
                            "markaziy_k": "Oromgoh ko‘chasi"
                        }
                    }
                }
            },
            "yuqori_chirchiq": {
                "name": "Yuqori Chirchiq tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Yangibozor» MFY",
                        "streets": {
                            "markaziy_k": "Yoshlik ko‘chasi"
                        }
                    }
                }
            },
            "yangiyol_t": {
                "name": "Yangiyo‘l tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Gulbahor» MFY",
                        "streets": {
                            "markaziy_k": "Guliston ko‘chasi"
                        }
                    }
                }
            },
            "zangiota": {
                "name": "Zangiota tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Zangiota» MFY",
                        "streets": {
                            "markaziy_k": "Eshonguzar ko‘chasi"
                        }
                    }
                }
            },
            "toshkent_t": {
                "name": "Toshkent tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Keles» MFY",
                        "streets": {
                            "markaziy_k": "Keles yo‘li ko‘chasi"
                        }
                    }
                }
            },
            "oqqorgon": {
                "name": "Oqqo‘rg‘on tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Oqqo‘rg‘on» MFY",
                        "streets": {
                            "markaziy_k": "Paxtakor ko‘chasi"
                        }
                    }
                }
            },
            "ohangaron": {
                "name": "Ohangaron tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Ohangaron» MFY",
                        "streets": {
                            "markaziy_k": "Ohangaron ko‘chasi"
                        }
                    }
                }
            }
        }
    },
    "fargona": {
        "name": "Farg‘ona viloyati",
        "districts": {
            "fargona_sh": {
                "name": "Farg‘ona shahri",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Ma’rifat» MFY",
                        "streets": {
                            "markaziy_k": "Sayilgoh ko‘chasi"
                        }
                    }
                }
            },
            "margilon_sh": {
                "name": "Marg‘ilon shahri",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Atlas» MFY",
                        "streets": {
                            "markaziy_k": "Ipakchilar ko‘chasi"
                        }
                    }
                }
            },
            "qoqon_sh": {
                "name": "Qo‘qon shahri",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Xudoyorxon» MFY",
                        "streets": {
                            "markaziy_k": "Turkiston ko‘chasi"
                        }
                    }
                }
            },
            "quvasoy_sh": {
                "name": "Quvasoy shahri",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Sementchi» MFY",
                        "streets": {
                            "markaziy_k": "Do‘stlik ko‘chasi"
                        }
                    }
                }
            },
            "oltiariq": {
                "name": "Oltiariq tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Oltiariq» MFY",
                        "streets": {
                            "markaziy_k": "Uzumzor ko‘chasi"
                        }
                    }
                }
            },
            "bagdod": {
                "name": "Bag‘dod tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Bag‘dod» MFY",
                        "streets": {
                            "markaziy_k": "Istiqlol ko‘chasi"
                        }
                    }
                }
            },
            "beshariq": {
                "name": "Beshariq tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Beshariq» MFY",
                        "streets": {
                            "markaziy_k": "Paxtakor ko‘chasi"
                        }
                    }
                }
            },
            "buvayda": {
                "name": "Buvayda tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Ibrat» MFY",
                        "streets": {
                            "markaziy_k": "Yangihayot ko‘chasi"
                        }
                    }
                }
            },
            "dangara": {
                "name": "Dang‘ara tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Dang‘ara» MFY",
                        "streets": {
                            "markaziy_k": "Buyuk ipak yo‘li ko‘chasi"
                        }
                    }
                }
            },
            "fargona_t": {
                "name": "Farg‘ona tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Vodil» MFY",
                        "streets": {
                            "markaziy_k": "Chashma ko‘chasi"
                        }
                    }
                }
            },
            "furqat": {
                "name": "Furqat tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Navbahor» MFY",
                        "streets": {
                            "markaziy_k": "Furqat ko‘chasi"
                        }
                    }
                }
            },
            "qoshtepa": {
                "name": "Qo‘shtepa tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Langar» MFY",
                        "streets": {
                            "markaziy_k": "Dehqon ko‘chasi"
                        }
                    }
                }
            },
            "quva": {
                "name": "Quva tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Al-Farg‘oniy» MFY",
                        "streets": {
                            "markaziy_k": "Ahmad Farg‘oniy ko‘chasi"
                        }
                    }
                }
            },
            "rishton": {
                "name": "Rishton tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Kulollar» MFY",
                        "streets": {
                            "markaziy_k": "Kulolchilik ko‘chasi"
                        }
                    }
                }
            },
            "sox": {
                "name": "So‘x tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Ravon» MFY",
                        "streets": {
                            "markaziy_k": "Tog‘ go‘zali ko‘chasi"
                        }
                    }
                }
            },
            "toshloq": {
                "name": "Toshloq tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Toshloq» MFY",
                        "streets": {
                            "markaziy_k": "Navoiy ko‘chasi"
                        }
                    }
                }
            },
            "uchkoprik": {
                "name": "Uchko‘prik tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Uchko‘prik» MFY",
                        "streets": {
                            "markaziy_k": "Bog‘ishamol ko‘chasi"
                        }
                    }
                }
            },
            "ozbekiston_t": {
                "name": "O‘zbekiston tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Yaypan» MFY",
                        "streets": {
                            "markaziy_k": "Yaypan ko‘chasi"
                        }
                    }
                }
            },
            "yozyovon": {
                "name": "Yozyovon tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Yozyovon» MFY",
                        "streets": {
                            "markaziy_k": "Markaziy ko‘cha"
                        }
                    }
                }
            }
        }
    },
    "xorazm": {
        "name": "Xorazm viloyati",
        "districts": {
            "urganch_sh": {
                "name": "Urganch shahri",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Al-Xorazmiy» MFY",
                        "streets": {
                            "markaziy_k": "Al-Xorazmiy shoh ko‘chasi"
                        }
                    }
                }
            },
            "xiva_sh": {
                "name": "Xiva shahri",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Ichan Qal’a» MFY",
                        "streets": {
                            "markaziy_k": "Polvon qori ko‘chasi"
                        }
                    }
                }
            },
            "bogot": {
                "name": "Bog‘ot tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Bog‘ot» MFY",
                        "streets": {
                            "markaziy_k": "Bog‘bon ko‘chasi"
                        }
                    }
                }
            },
            "gurlan": {
                "name": "Gurlan tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Gurlan» MFY",
                        "streets": {
                            "markaziy_k": "Paxtakor ko‘chasi"
                        }
                    }
                }
            },
            "xonqa": {
                "name": "Xonqa tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Xonqa» MFY",
                        "streets": {
                            "markaziy_k": "Istiqlol ko‘chasi"
                        }
                    }
                }
            },
            "hazorasp": {
                "name": "Hazorasp tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Hazorasp» MFY",
                        "streets": {
                            "markaziy_k": "Amudaryo ko‘chasi"
                        }
                    }
                }
            },
            "xiva_t": {
                "name": "Xiva tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Gandimiyon» MFY",
                        "streets": {
                            "markaziy_k": "Tarixiy ko‘cha"
                        }
                    }
                }
            },
            "qoshkopir": {
                "name": "Qo‘shko‘pir tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Qo‘shko‘pir» MFY",
                        "streets": {
                            "markaziy_k": "Yoshlik ko‘chasi"
                        }
                    }
                }
            },
            "shovot": {
                "name": "Shovot tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Shovot» MFY",
                        "streets": {
                            "markaziy_k": "Turkiston ko‘chasi"
                        }
                    }
                }
            },
            "urganch_t": {
                "name": "Urganch tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Qorovul» MFY",
                        "streets": {
                            "markaziy_k": "Jayhun ko‘chasi"
                        }
                    }
                }
            },
            "yangiariq": {
                "name": "Yangiariq tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Yangiariq» MFY",
                        "streets": {
                            "markaziy_k": "Guliston ko‘chasi"
                        }
                    }
                }
            },
            "yangibozor": {
                "name": "Yangibozor tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Yangibozor» MFY",
                        "streets": {
                            "markaziy_k": "Mustaqillik ko‘chasi"
                        }
                    }
                }
            },
            "tuproqqala": {
                "name": "Tuproqqal’a tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Pitaq» MFY",
                        "streets": {
                            "markaziy_k": "Konchilar ko‘chasi"
                        }
                    }
                }
            }
        }
    },
    "toshkent_sh": {
        "name": "Toshkent shahri",
        "districts": {
            "bektemir": {
                "name": "Bektemir tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Majnuntol» MFY",
                        "streets": {
                            "markaziy_k": "Bektemir shoh ko‘chasi"
                        }
                    }
                }
            },
            "chilonzor": {
                "name": "Chilonzor tumani",
                "mfys": {
                    "katartol": {
                        "name": "«Qatortol» MFY",
                        "streets": {
                            "qatortol": "Qatortol ko‘chasi"
                        }
                    }
                }
            },
            "mirobod": {
                "name": "Mirobod tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Mirobod» MFY",
                        "streets": {
                            "markaziy_k": "Nukus ko‘chasi"
                        }
                    }
                }
            },
            "mirzo_ulugbek": {
                "name": "Mirzo Ulug‘bek tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Buyuk Ipak Yo‘li» MFY",
                        "streets": {
                            "markaziy_k": "Mustaqillik shoh ko‘chasi"
                        }
                    }
                }
            },
            "olmazor": {
                "name": "Olmazor tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Qorasaroy» MFY",
                        "streets": {
                            "markaziy_k": "Zarqaynar ko‘chasi"
                        }
                    }
                }
            },
            "sergeli": {
                "name": "Sergeli tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Qipchoq» MFY",
                        "streets": {
                            "markaziy_k": "Yangi Sergeli ko‘chasi"
                        }
                    }
                }
            },
            "shayxontohur": {
                "name": "Shayxontohur tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Chorsu» MFY",
                        "streets": {
                            "markaziy_k": "Navoiy shoh ko‘chasi"
                        }
                    }
                }
            },
            "uchtepa": {
                "name": "Uchtepa tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Farhod» MFY",
                        "streets": {
                            "markaziy_k": "Lutfiy ko‘chasi"
                        }
                    }
                }
            },
            "yakkasaroy": {
                "name": "Yakkasaroy tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Bobur» MFY",
                        "streets": {
                            "markaziy_k": "Shota Rustaveli ko‘chasi"
                        }
                    }
                }
            },
            "yangihayot": {
                "name": "Yangihayot tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Yangi Darxon» MFY",
                        "streets": {
                            "markaziy_k": "Binokor ko‘chasi"
                        }
                    }
                }
            },
            "yunusobod": {
                "name": "Yunusobod tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Yangi ariq» MFY",
                        "streets": {
                            "markaziy_k": "Amir Temur shoh ko‘chasi"
                        }
                    }
                }
            },
            "yashnobod": {
                "name": "Yashnobod tumani",
                "mfys": {
                    "markaz_mfy": {
                        "name": "«Do‘stlik» MFY",
                        "streets": {
                            "markaziy_k": "Farg‘ona yo‘li ko‘chasi"
                        }
                    }
                }
            }
        }
    }
}

# ========================================================
# 2. FOYDALANUVCHILARNI SAQLASH (DATABASE)
# ========================================================
def load_subscribers():
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("Error loading subscribers:", e)
        return {}

def save_subscribers(subs):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(subs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Error saving subscribers:", e)

def normalize_phone(raw):
    """Telefon raqamni tozalab, +998 (XX) XXX-XX-XX ko'rinishiga keltiradi"""
    if not raw:
        return None, None
    digits = re.sub(r"\D", "", str(raw))
    if len(digits) == 9:
        digits = "998" + digits
    if len(digits) == 12 and digits.startswith("998"):
        formatted = f"+998 ({digits[3:5]}) {digits[5:8]}-{digits[8:10]}-{digits[10:12]}"
        return digits, formatted
    if len(digits) >= 9 and len(digits) <= 15:
        return digits, f"+{digits}"
    return None, None

def safe_html(text):
    return html.escape(str(text or ""))

# ========================================================
# 3. TELEGRAM BOT API YORDAMCHI FUNKSIYALARI
# ========================================================
def tg_request(method, payload=None):
    url = f"{API_URL}/{method}"
    try:
        data = None
        headers = {"User-Agent": "XonadonPlusBot/1.0"}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        print(f"[Telegram API Error] {method}: HTTP {e.code} -> {err_body}")
        return None
    except Exception as e:
        print(f"Telegram API request failed ({method}):", e)
        return None

def send_message(chat_id, text, reply_markup=None, parse_mode="HTML"):
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if reply_markup:
        payload["reply_markup"] = reply_markup
    res = tg_request("sendMessage", payload)
    # Agar parse_mode xatolik bergan bo'lsa, xom matn sifatida qayta jo'natish (Fail-safe)
    if res is None and parse_mode:
        plain_text = re.sub(r"<[^>]+>", "", text)
        payload["text"] = plain_text
        payload.pop("parse_mode", None)
        return tg_request("sendMessage", payload)
    return res

def edit_message_text(chat_id, message_id, text, reply_markup=None, parse_mode="HTML"):
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if reply_markup:
        payload["reply_markup"] = reply_markup
    res = tg_request("editMessageText", payload)
    if res is None and parse_mode:
        plain_text = re.sub(r"<[^>]+>", "", text)
        payload["text"] = plain_text
        payload.pop("parse_mode", None)
        return tg_request("editMessageText", payload)
    return res

def answer_callback(callback_query_id, text=None):
    payload = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
    return tg_request("answerCallbackQuery", payload)

# ========================================================
# 4. KLAVIATURALAR VA MENYULAR
# ========================================================
def get_contact_keyboard():
    return {
        "keyboard": [
            [{"text": "📱 Telefon raqamni ulashish", "request_contact": True}]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": True
    }

def get_otp_keyboard():
    return {
        "keyboard": [
            [{"text": "⬅️ Boshqa raqam kiritish"}]
        ],
        "resize_keyboard": True
    }

def get_main_keyboard(chat_id=None):
    addr_btn_text = "📍 Manzilimni biriktirish"
    if chat_id is not None:
        try:
            subs = load_subscribers()
            u = subs.get(str(chat_id), {})
            if u.get("address_text") or (u.get("address") and u.get("address", {}).get("street_label")):
                addr_btn_text = "✏️ Manzilni o‘zgartirish"
        except Exception:
            pass

    return {
        "keyboard": [
            [{"text": addr_btn_text}, {"text": "🚚 Gaz mashinasi qayerda?"}],
            [{"text": "💳 Balon uchun to‘lov"}, {"text": "🛡️ Xavfsizlik qoidalari"}],
            [{"text": "👤 Profilim va Telefon raqam"}]
        ],
        "resize_keyboard": True
    }

def get_region_keyboard():
    short_names = {
        "qoraqalpogiston": "Qoraqalpog‘iston Resp.",
        "andijon": "Andijon vil.",
        "buxoro": "Buxoro vil.",
        "jizzax": "Jizzax vil.",
        "qashqadaryo": "Qashqadaryo vil.",
        "navoiy": "Navoiy vil.",
        "namangan": "Namangan vil.",
        "samarqand": "Samarqand vil.",
        "surxondaryo": "Surxondaryo vil.",
        "sirdaryo": "Sirdaryo vil.",
        "toshkent_vil": "Toshkent vil.",
        "fargona": "Farg‘ona vil.",
        "xorazm": "Xorazm vil.",
        "toshkent_sh": "Toshkent shahri"
    }
    buttons = []
    row = []
    for r_key, r_val in ADDRESS_DB.items():
        title = short_names.get(r_key, r_val['name'])
        row.append({"text": f"📍 {title}", "callback_data": f"reg:{r_key}"})
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return {"inline_keyboard": buttons}

def get_district_keyboard(reg_key):
    districts = ADDRESS_DB.get(reg_key, {}).get("districts", {})
    buttons = []
    row = []
    for d_key, d_val in districts.items():
        row.append({"text": f"🏛 {d_val['name']}", "callback_data": f"dist:{reg_key}:{d_key}"})
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([{"text": "⬅️ Ortga", "callback_data": "back_to_reg"}])
    return {"inline_keyboard": buttons}

def get_mfy_keyboard(reg_key, dist_key):
    mfys = ADDRESS_DB.get(reg_key, {}).get("districts", {}).get(dist_key, {}).get("mfys", {})
    buttons = []
    row = []
    for m_key, m_val in mfys.items():
        row.append({"text": f"🏡 {m_val['name']}", "callback_data": f"mfy:{reg_key}:{dist_key}:{m_key}"})
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([{"text": "⬅️ Ortga", "callback_data": f"reg:{reg_key}"}])
    return {"inline_keyboard": buttons}

def get_street_keyboard(reg_key, dist_key, mfy_key):
    streets = ADDRESS_DB.get(reg_key, {}).get("districts", {}).get(dist_key, {}).get("mfys", {}).get(mfy_key, {}).get("streets", {})
    buttons = []
    row = []
    for s_key, s_val in streets.items():
        row.append({"text": f"🛣 {s_val}", "callback_data": f"st:{reg_key}:{dist_key}:{mfy_key}:{s_key}"})
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([{"text": "⬅️ Ortga", "callback_data": f"dist:{reg_key}:{dist_key}"}])
    return {"inline_keyboard": buttons}


# ========================================================
# 5. XABARNOMALARNI TARQATISH (DRIVER DISPATCH)
# ========================================================
current_driver_state = {
    "region": "qashqadaryo",
    "district": "nishon",
    "mfy": "yangi_nishon",
    "street": "istiqlol",
    "stage": "collect",
    "status": "arrived",
    "truck_model": "Isuzu NPR 75",
    "truck_plate": "30 782 AGA",
    "truck_color": "Oq (Sariq chiziqli)",
    "driver_name": "Islomov Javohir",
    "driver_phone": "+998 (90) 123-45-67",
    "last_address_text": "Qashqadaryo viloyati, Nishon tumani, «Yangi Nishon» MFY, Istiqlol ko‘chasi",
    "last_alert_time": None
}

def broadcast_street_alert(street_key, reg_key="qashqadaryo", dist_key="nishon", mfy_key="yangi_nishon", stage="collect",
                           status="arrived",
                           reg_name=None, dist_name=None, mfy_name=None, street_name=None,
                           truck_model="Isuzu NPR 75", truck_plate="30 782 AGA", truck_color="Oq (Sariq chiziqli)",
                           driver_name="Islomov Javohir", driver_phone="+998 (90) 123-45-67"):
    subs = load_subscribers()
    if not subs:
        print("[BOT] Hozircha obunachilar yo‘q.")
        return 0

    current_driver_state["stage"] = stage
    current_driver_state["status"] = status or "arrived"
    current_driver_state["truck_model"] = truck_model or current_driver_state.get("truck_model", "Isuzu NPR 75")
    current_driver_state["truck_plate"] = truck_plate or current_driver_state.get("truck_plate", "30 782 AGA")
    current_driver_state["truck_color"] = truck_color or current_driver_state.get("truck_color", "Oq (Sariq chiziqli)")
    current_driver_state["driver_name"] = driver_name or current_driver_state["driver_name"]
    current_driver_state["driver_phone"] = driver_phone or current_driver_state["driver_phone"]
    current_driver_state["region"] = reg_key
    current_driver_state["district"] = dist_key
    current_driver_state["mfy"] = mfy_key
    current_driver_state["street"] = street_key

    # Inson tushunadigan to'liq manzil nomlarini aniqlash (Payload nomlaridan yoki bazadan)
    if not reg_name:
        reg_name = ADDRESS_DB.get(reg_key, {}).get("name", reg_key)
    if not dist_name:
        dist_name = ADDRESS_DB.get(reg_key, {}).get("districts", {}).get(dist_key, {}).get("name", dist_key)
    if not mfy_name:
        mfy_name = ADDRESS_DB.get(reg_key, {}).get("districts", {}).get(dist_key, {}).get("mfys", {}).get(mfy_key, {}).get("name", mfy_key)
    if not street_name:
        street_name = ADDRESS_DB.get(reg_key, {}).get("districts", {}).get(dist_key, {}).get("mfys", {}).get(mfy_key, {}).get("streets", {}).get(street_key, street_key)

    full_address = f"{reg_name}, {dist_name}, {mfy_name}, {street_name}"
    current_driver_state["last_address_text"] = full_address

    is_collect = (stage == "collect")
    stage_badge = "🟢 1-BOSQICH: BO‘SH BALONLARNI YIG‘IB OLISH" if is_collect else "🔵 2-BOSQICH: TO‘LDIRILGAN BALONLARNI TARQATISH"
    
    stage_guide = (
        "⚠️ <b>Ko‘rsatma:</b> Iltimos, bo‘sh gaz baloningizni xavfsizlik qoidalariga rioya qilgan holda ko‘chaga olib chiqing! "
        "Haydovchi navbat bilan har bir xonadondan bo‘sh balonlarni qabul qilib olmoqda va to‘ldirish uchun gaz bazasiga yetkazadi."
        if is_collect else
        "⚠️ <b>Ko‘rsatma:</b> Gaz bazasidan to‘ldirib kelingan yangi gaz balonlari tarqatilmoqda! "
        "Baloningizni qabul qilib oling, xavfsizlik klapanini tekshiring va kvitansiyani oling."
    )

    t_model = current_driver_state.get("truck_model") or "Isuzu NPR 75"
    t_plate = current_driver_state.get("truck_plate") or "30 782 AGA"
    t_color = current_driver_state.get("truck_color") or "Oq (Sariq chiziqli)"

    if status == "on_the_way":
        alert_text = (
            f"🛣️ <b>DIQQAT! HAYDOVCHI YO‘LDA (KO‘CHAGA CHIQDIK)!</b> 🚨\n\n"
            f"📍 <b>Manzil:</b> <b>{safe_html(full_address)}</b>\n"
            f"🚗 <i>Haydovchi hozirda sizning ko‘changiz tomon yo‘lga chiqdi va tez orada yetib keladi. Iltimos, bo‘sh gaz baloningizni ko‘chaga olib chiqishga tayyorlab turing!</i>\n\n"
            f"📌 <b>Harakat bosqichi:</b>\n👉 <b>{safe_html(stage_badge)}</b>\n\n"
            f"🚛 <b>Maxsus mashina:</b> {safe_html(t_model)} (<code>{safe_html(t_plate)}</code>)\n"
            f"🎨 <b>Mashina rangi:</b> {safe_html(t_color)}\n"
            f"👨‍✈️ <b>Haydovchi:</b> {safe_html(current_driver_state['driver_name'])}\n"
            f"📞 <b>Aloqa:</b> <code>{safe_html(current_driver_state['driver_phone'])}</code>\n"
            f"💰 <b>Davlat tarifi:</b> <b>20 000 so‘m</b> (1 dona balon)\n"
            f"⏳ <b>Taxminiy yetib kelish vaqti:</b> <b>~10-15 daqiqa</b>\n\n"
            f"{stage_guide}\n\n"
            f"⏱ <i>Xabar yuborilgan vaqt: {time.strftime('%H:%M, %d.%m.%Y')}</i>\n"
            f"🔥 <b>Xonadon+ Smart Mahalla Tizimi</b>"
        )
    else:
        alert_text = (
            f"🚨 <b>DIQQAT! GAZ MASHINASI SIZNING KO‘CHANGIZGA KIRDI!</b> 🚨\n\n"
            f"📍 <b>Manzil:</b> <b>{safe_html(full_address)}</b>\n"
            f"📌 <b>Harakat bosqichi:</b>\n👉 <b>{safe_html(stage_badge)}</b>\n\n"
            f"🚛 <b>Maxsus mashina:</b> {safe_html(t_model)} (<code>{safe_html(t_plate)}</code>)\n"
            f"🎨 <b>Mashina rangi:</b> {safe_html(t_color)}\n"
            f"👨‍✈️ <b>Haydovchi:</b> {safe_html(current_driver_state['driver_name'])}\n"
            f"📞 <b>Aloqa:</b> <code>{safe_html(current_driver_state['driver_phone'])}</code>\n"
            f"💰 <b>Davlat tarifi:</b> <b>20 000 so‘m</b> (1 dona balon)\n\n"
            f"{stage_guide}\n\n"
            f"⏱ <i>Xabar yuborilgan vaqt: {time.strftime('%H:%M, %d.%m.%Y')}</i>\n"
            f"🔥 <b>Xonadon+ Smart Mahalla Tizimi</b>"
        )

    action_keyboard = {
        "inline_keyboard": [
            [
                {"text": "💳 Balon uchun to‘lash (20 000 so‘m)", "callback_data": "pay_lpg_now"},
                {"text": "🛡️ Xavfsizlik qoidalari", "callback_data": "show_safety"}
            ],
            [
                {"text": "📞 Haydovchi bilan bog‘lanish", "callback_data": "call_driver"}
            ]
        ]
    }

    sent_count = 0
    now_time = time.strftime('%H:%M, %d.%m.%Y')
    current_driver_state["last_alert_time"] = now_time

    # =========================================================================
    # MFY BO'YICHA ANIQ FILTR: BOSHQA TUMAN/MFYGA BORMAYDI, FAQAT SHU MFY AHOLISIGA YETKAZILADI
    # =========================================================================
    for cid_str, udata in subs.items():
        user_addr = udata.get("address", {})
        u_reg = user_addr.get("region", "")
        u_dist = user_addr.get("district", "")
        u_mfy = user_addr.get("mfy", "")
        u_street = user_addr.get("street", "")
        u_label = (user_addr.get("street_label") or "").lower()

        norm_target_street = (street_key or "").lower().strip()
        norm_user_street = (u_street or "").lower().strip()
        norm_target_mfy = (mfy_key or "").lower().strip()
        norm_user_mfy = (u_mfy or "").lower().strip()
        norm_target_dist = (dist_key or "").lower().strip()
        norm_user_dist = (u_dist or "").lower().strip()

        # 1. Bitta MFY ekanligini qat'iy tekshirish
        mfy_match = False
        if norm_target_mfy and norm_user_mfy and (norm_target_mfy == norm_user_mfy):
            dist_ok = (not norm_target_dist or not norm_user_dist or norm_target_dist == norm_user_dist)
            if dist_ok:
                mfy_match = True
        elif not norm_user_mfy and mfy_name:
            mfy_clean = mfy_name.lower().replace("mfy", "").replace("«", "").replace("»", "").strip()
            if mfy_clean and mfy_clean in u_label:
                mfy_match = True

        # Agar fuqaro boshqa MFYda bo'lsa -> Xabar umuman bormaydi!
        if not mfy_match:
            continue

        # 2. Fuqaroning o'z ko'chasimi yoki mahalladagi boshqa ko'chami?
        is_user_street = False
        if norm_target_street and norm_user_street and (norm_target_street == norm_user_street):
            is_user_street = True
        elif street_name:
            st_clean = street_name.lower().replace("ko‘chasi", "").replace("ko'chasi", "").replace("kochasi", "").strip()
            if st_clean and st_clean in u_label:
                is_user_street = True

        # Mos xabar matnini tanlash
        if is_user_street:
            msg_to_send = alert_text
        else:
            msg_to_send = (
                f"📢 <b>DIQQAT! GAZ MASHINASI MAHALLANGIZDAGI «{safe_html(street_name)}» KO‘CHASIGA KIRDI!</b>\n\n"
                f"📍 <b>Hozirgi xizmat manzili:</b> <b>{safe_html(full_address)}</b>\n"
                f"🏠 <i>Sizning ko‘changiz: {safe_html(user_addr.get('street_label', 'Mahallangiz'))}</i>\n"
                f"⏳ <i>Mashina navbat bilan sizning ko‘changizga ham yetib keladi.</i>\n\n"
                f"📌 <b>Harakat bosqichi:</b>\n👉 <b>{safe_html(stage_badge)}</b>\n\n"
                f"🚛 <b>Maxsus mashina:</b> {safe_html(t_model)} (<code>{safe_html(t_plate)}</code>)\n"
                f"🎨 <b>Mashina rangi:</b> {safe_html(t_color)}\n"
                f"👨‍✈️ <b>Haydovchi:</b> {safe_html(current_driver_state['driver_name'])}\n"
                f"📞 <b>Aloqa:</b> <code>{safe_html(current_driver_state['driver_phone'])}</code>\n"
                f"💰 <b>Davlat tarifi:</b> <b>20 000 so‘m</b> (1 dona balon)\n\n"
                f"{stage_guide}\n\n"
                f"⏱ <i>Xabar yuborilgan vaqt: {time.strftime('%H:%M, %d.%m.%Y')}</i>\n"
                f"🔥 <b>Xonadon+ Smart Mahalla Tizimi</b>"
            )

        try:
            cid = int(cid_str)
            res = send_message(cid, msg_to_send, reply_markup=action_keyboard, parse_mode="HTML")
            if res and res.get("ok"):
                sent_count += 1
            time.sleep(0.04)
        except Exception as e:
            print(f"[BOT] Xabar yuborishda xatolik ({cid_str}):", e)

    if sent_count == 0:
        print(f"[BOT] «{full_address}» MFY bo‘yicha hozircha botda obunachi topilmadi.")
    else:
        print(f"[BOT] MFY filtri: «{full_address}» mahallasi bo‘yicha {sent_count} ta fuqaroga xabar yetkazildi.")
    return sent_count

# ========================================================
# 6. FOYDALANUVCHI BUYRUQLARI VA IDENTIFIKATSIYA
# ========================================================
def handle_start(chat_id, user_info):
    subs = load_subscribers()
    cid_str = str(chat_id)
    if cid_str not in subs:
        subs[cid_str] = {
            "chat_id": chat_id,
            "first_name": user_info.get("first_name", ""),
            "username": user_info.get("username", ""),
            "registered_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "phone_verified": False,
            "status": "unverified",
            "phone": None,
            "address": {
                "region": "qashqadaryo",
                "district": "nishon",
                "mfy": "yangi_nishon",
                "street": "istiqlol",
                "street_label": "Qashqadaryo viloyati, Nishon tumani, «Yangi Nishon» MFY, Istiqlol ko‘chasi"
            }
        }
        save_subscribers(subs)

    user_sub = subs[cid_str]
    u_name = safe_html(user_info.get("first_name", "Hurmatli fuqaro"))

    # Agar telefon raqami tasdiqlanmagan bo'lsa -> Kontakt yoki raqam kiritish so'raladi
    if not user_sub.get("phone_verified"):
        user_sub["status"] = "unverified"
        save_subscribers(subs)

        prompt_text = (
            f"Assalomu alaykum, <b>{u_name}</b>!\n\n"
            f"🔥 <b>Xonadon+</b> — Suyultirilgan gaz balonlarini xonadonlarga tarqatish "
            f"va avtomatlashtirilgan monitoring rasmiy botiga xush kelibsiz!\n\n"
            f"🔐 <b>XAVFSIZLIK VA IDENTIFIKATSIYA:</b>\n"
            f"Boshqa shaxslar sizning nomingizdan hisobingizga kira olmasligi hamda "
            f"ilovadagi xonadoningiz bilan Telegram botni xavfsiz bog‘lash uchun "
            f"telefon raqamingizni tasdiqlashingiz lozim.\n\n"
            f"<b>Quyidagi usullardan birini tanlang:</b>\n"
            f"1️⃣ Pastdagi <b>«📱 Telefon raqamni ulashish»</b> tugmasini bosing (Telegram orqali tezkor va xavfsiz)\n"
            f"2️⃣ Yoki telefon raqamingizni yozib yuboring (Masalan: <code>+998940401009</code>) — raqamingizga 4 xonali SMS kod yuboriladi."
        )
        send_message(chat_id, prompt_text, reply_markup=get_contact_keyboard(), parse_mode="HTML")
        return

    # Agar allaqachon tasdiqlangan bo'lsa -> Asosiy menyu ko'rsatiladi
    phone_display = safe_html(user_sub.get("phone", "+998 (94) 040-10-09"))
    u_addr = safe_html(user_sub.get("address", {}).get("street_label", "Istiqlol ko‘chasi"))

    welcome_text = (
        f"Assalomu alaykum, <b>{u_name}</b>!\n\n"
        f"🔥 <b>Xonadon+</b> tizimiga xush kelibsiz!\n\n"
        f"✅ <b>Tasdiqlangan telefon:</b> <code>{phone_display}</code>\n"
        f"📍 <b>Joriy biriktirilgan ko‘changiz:</b>\n<i>{u_addr}</i>\n\n"
        f"🔔 Haydovchi sizning ko‘changizga kirganda «Ko‘chaga kirdik» tugmasini bosishi bilan "
        f"ushbu Telegramingizga <b>avtomatik ovozli bildirishnoma</b> yetib keladi.\n\n"
        f"Quyidagi menyudan kerakli bo‘limni tanlang 👇"
    )
    send_message(chat_id, welcome_text, reply_markup=get_main_keyboard(chat_id), parse_mode="HTML")

def handle_message(msg):
    chat_id = msg["chat"]["id"]
    user_info = msg.get("from", {})
    cid_str = str(chat_id)
    subs = load_subscribers()

    if cid_str not in subs:
        subs[cid_str] = {
            "chat_id": chat_id,
            "first_name": user_info.get("first_name", ""),
            "username": user_info.get("username", ""),
            "registered_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "phone_verified": False,
            "status": "unverified",
            "phone": None,
            "address": {
                "region": "qashqadaryo",
                "district": "nishon",
                "mfy": "yangi_nishon",
                "street": "istiqlol",
                "street_label": "Qashqadaryo viloyati, Nishon tumani, «Yangi Nishon» MFY, Istiqlol ko‘chasi"
            }
        }
        save_subscribers(subs)

    user_sub = subs[cid_str]

    # 1. KONTAKT ULASHILGANDA (request_contact TUGMASI ORQALI)
    if "contact" in msg:
        c_user_id = msg["contact"].get("user_id")
        sender_id = msg["from"]["id"]
        raw_phone = msg["contact"].get("phone_number")
        digits, formatted = normalize_phone(raw_phone)

        # Telegram o'zining haqiqiy kontakti bo'lsa -> Birdan tasdiqlanadi (Kriptografik kafolat)
        if digits and c_user_id == sender_id:
            user_sub["raw_phone"] = digits
            user_sub["phone"] = formatted
            user_sub["phone_verified"] = True
            user_sub["status"] = "awaiting_address"
            user_sub["phone_verified_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            save_subscribers(subs)

            conf_text = (
                f"🎉 <b>TABRIKLAYMIZ! TELEFONINGIZ TASDIQLANDI!</b>\n\n"
                f"📱 <b>Telefon raqam:</b> <code>{formatted}</code> ✅\n"
                f"🛡️ <b>Tasdiqlash usuli:</b> Telegram rasmiy kontakti\n\n"
                f"📍 <b>Endi yashash manzilingizni tanlang:</b>\n"
                f"<i>Tizimda xatoliklar bo‘lmasligi uchun viloyat, tuman, mahalla va ko‘changizni pastdagi tugmalar orqali ketma-ket tanlang:</i>"
            )
            send_message(chat_id, conf_text, reply_markup=get_region_keyboard(), parse_mode="HTML")
            return
        elif digits:
            # Agar boshqa odamning kontakti uzatilgan bo'lsa -> SMS kod talab qilinadi
            user_sub["pending_phone"] = formatted
            user_sub["pending_raw"] = digits
            user_sub["pending_otp"] = "7824"
            user_sub["status"] = "awaiting_otp"
            save_subscribers(subs)

            prompt_otp = (
                f"📩 <b>SMS TASDIQLASH KODI YUBORILDI!</b>\n\n"
                f"📱 <b>Raqam:</b> <code>{formatted}</code>\n"
                f"🔐 Xavfsizlik maqsadida ushbu raqamga 4 xonali SMS kod yuborildi.\n\n"
                f"[🔔 <b>Demo rejimda SMS kod:</b> <code>7824</code>]\n\n"
                f"Iltimos, ushbu telefon raqami aynan sizga tegishli ekanligini tasdiqlash uchun 4 xonali kodni yozib yuboring (Masalan: <code>7824</code>):"
            )
            send_message(chat_id, prompt_otp, reply_markup=get_otp_keyboard(), parse_mode="HTML")
            return

    text = msg.get("text", "").strip()

    # --- ADMIN BOSHQARUVI (/admin_login yoki /admin) ---
    if text.startswith("/admin_login") or text == "/admin":
        parts = text.split()
        if text == "/admin" and not db_manager.is_bot_admin(chat_id):
            send_message(chat_id, "🔐 <b>Admin sifatida kirish:</b>\nIltimos, maxsus admin parolini kiriting:\nMasalan: <code>/admin_login GazAdmin2026</code>", parse_mode="HTML")
            return
        elif len(parts) > 1 and parts[1] == "GazAdmin2026" or db_manager.is_bot_admin(chat_id):
            db_manager.add_bot_admin(chat_id, user_info.get("first_name", "Admin"), user_info.get("username", ""))
            admin_menu_text = (
                "👑 <b>XONADON+ BOSHQARUV PANELI (BOSH ADMIN)</b>\n\n"
                "Xush kelibsiz, Administrator! Ushbu bo‘lim faqat sizga ko‘rinadi.\n"
                "Tizimni quyidagi buyruqlar orqali boshqarishingiz mumkin:\n\n"
                "➕ <b>/add_driver</b> — Yangi haydovchi qo‘shish (Login & Parol berish)\n"
                "📋 <b>/drivers</b> — Barcha faol haydovchilar ro‘yxati\n"
                "👥 <b>/users</b> — Ro‘yxatdan o‘tgan fuqarolar statistikasi\n"
                "🚪 <b>/exit_admin</b> — Admin rejimidan chiqish"
            )
            keyboard = {
                "keyboard": [
                    [{"text": "➕ Yangi haydovchi qo‘shish"}],
                    [{"text": "📋 Haydovchilar ro‘yxati"}, {"text": "👥 Fuqarolar statistikasi"}],
                    [{"text": "⬅️ Asosiy menyuga qaytish"}]
                ],
                "resize_keyboard": True
            }
            send_message(chat_id, admin_menu_text, reply_markup=keyboard, parse_mode="HTML")
            return

    # Admin actions
    if db_manager.is_bot_admin(chat_id):
        if text == "➕ Yangi haydovchi qo‘shish" or text == "/add_driver":
            user_sub["admin_state"] = "awaiting_driver_name"
            save_subscribers(subs)
            msg_prompt = (
                "➕ <b>YANGI HAYDOVCHI QO‘SHISH (1/4-bosqich)</b>\n\n"
                "1️⃣ Iltimos, yangi haydovchining <b>Ism va Familiyasini</b> kiriting:\n"
                "<i>(Masalan: Ahror Suyunov)</i>"
            )
            send_message(chat_id, msg_prompt, parse_mode="HTML")
            return

        # 1-bosqich: Ism-familiya kiritildi -> Telefon raqam so'rash
        elif user_sub.get("admin_state") == "awaiting_driver_name":
            # Check if user passed full line with pipes fallback
            if "|" in text:
                parts = [p.strip() for p in text.split("|")]
                if len(parts) >= 3:
                    d_name = parts[0]
                    d_phone = parts[1]
                    d_plate = parts[2]
                    d_pass = parts[3] if len(parts) > 3 else "gaz2026"
                    db_manager.add_driver(phone=d_phone, full_name=d_name, truck_plate=d_plate, password=d_pass, assigned_mfy="koksoy")
                    user_sub.pop("admin_state", None)
                    save_subscribers(subs)
                    send_message(chat_id, f"✅ <b>HAYDOVCHI QO‘SHILDI!</b>\n👤 {d_name}\n📱 {d_phone}\n🚛 {d_plate}\n🔑 {d_pass}", parse_mode="HTML")
                    return

            d_name = text.strip()
            user_sub["new_d_name"] = d_name
            user_sub["admin_state"] = "awaiting_driver_phone"
            save_subscribers(subs)
            prompt = (
                f"👤 <b>Haydovchi:</b> {d_name} ✅\n\n"
                "2️⃣ Endi haydovchining <b>Telefon raqamini</b> kiriting:\n"
                "<i>(Masalan: +998940401009)</i>"
            )
            send_message(chat_id, prompt, parse_mode="HTML")
            return

        # 2-bosqich: Telefon kiritildi -> Mashina raqamini so'rash
        elif user_sub.get("admin_state") == "awaiting_driver_phone":
            d_phone = text.strip()
            user_sub["new_d_phone"] = d_phone
            user_sub["admin_state"] = "awaiting_driver_plate"
            save_subscribers(subs)
            prompt = (
                f"📱 <b>Telefon:</b> <code>{d_phone}</code> ✅\n\n"
                "3️⃣ Endi gaz mashinasining <b>Davlat raqamini</b> kiriting:\n"
                "<i>(Masalan: 70 M 260 EB yoki 70M260EB)</i>"
            )
            send_message(chat_id, prompt, parse_mode="HTML")
            return

        # 3-bosqich: Mashina raqami kiritildi -> Parol so'rash
        elif user_sub.get("admin_state") == "awaiting_driver_plate":
            raw_plate = text.strip().upper()
            user_sub["new_d_plate"] = raw_plate
            user_sub["admin_state"] = "awaiting_driver_password"
            save_subscribers(subs)
            prompt = (
                f"🚛 <b>Mashina raqami:</b> <code>{raw_plate}</code> ✅\n\n"
                "4️⃣ Endi haydovchining <b>Maxsus kirish parolini</b> kiriting:\n"
                "<i>(Masalan: GENTRA yoki gaz2026)</i>"
            )
            send_message(chat_id, prompt, parse_mode="HTML")
            return

        # 4-bosqich: Parol kiritildi -> Bazaga saqlash va yakunlash
        elif user_sub.get("admin_state") == "awaiting_driver_password":
            d_pass = text.strip()
            d_name = user_sub.get("new_d_name", "Haydovchi")
            d_phone = user_sub.get("new_d_phone", "+998901234567")
            d_plate = user_sub.get("new_d_plate", "30 782 AGA")

            res = db_manager.add_driver(
                phone=d_phone,
                full_name=d_name,
                truck_plate=d_plate,
                password=d_pass,
                assigned_mfy="koksoy"
            )

            user_sub.pop("admin_state", None)
            user_sub.pop("new_d_name", None)
            user_sub.pop("new_d_phone", None)
            user_sub.pop("new_d_plate", None)
            save_subscribers(subs)

            succ_text = (
                "✅ <b>HAYDOVCHI MUVAFFAQIYATLI QO‘SHILDI!</b>\n\n"
                f"👤 <b>F.I.Sh:</b> {d_name}\n"
                f"📱 <b>Login (Telefon):</b> <code>{d_phone}</code>\n"
                f"🚛 <b>Mashina raqami:</b> <code>{d_plate}</code>\n"
                f"📍 <b>Hudud:</b> «Ko‘ksoy» MFY, Nishon tumani\n"
                f"🔑 <b>Kirish paroli:</b> <code>{d_pass}</code>\n\n"
                "Endi haydovchi ilovaga ushbu telefon, mashina raqami va parol orqali kira oladi!"
            )
            send_message(chat_id, succ_text, parse_mode="HTML")
            return

        elif text == "📋 Haydovchilar ro‘yxati" or text == "/drivers":
            drivers = db_manager.get_all_drivers()
            if not drivers:
                send_message(chat_id, "Hozircha tizimda haydovchilar yo‘q.")
                return
            send_message(chat_id, "📋 <b>TIZIMDAGI HAYDOVCHILAR:</b>\n<i>O‘chirish uchun kerakli haydovchi ostidagi tugmani bosing:</i>", parse_mode="HTML")
            for d in drivers:
                d_phone = d.get('phone', '')
                d_name = d.get('full_name', '')
                d_plate = d.get('truck_plate', '')
                d_model = d.get('truck_model', 'Isuzu NPR 75')
                d_pass = d.get('password', '')

                d_item = (
                    f"• <b>{safe_html(d_name)}</b>\n"
                    f"  📱 Tel/Login: <code>{safe_html(d_phone)}</code> | Parol: <code>{safe_html(d_pass)}</code>\n"
                    f"  🚛 Mashina: <b>{safe_html(d_plate)}</b> ({safe_html(d_model)})"
                )
                inline_del = {
                    "inline_keyboard": [
                        [{"text": f"❌ {safe_html(d_name)} ({d_plate}) ni o‘chirish", "callback_data": f"deldriver_{d_phone}"}]
                    ]
                }
                send_message(chat_id, d_item, reply_markup=inline_del, parse_mode="HTML")
            return

        elif text == "👥 Fuqarolar statistikasi" or text == "/users":
            conn = db_manager.get_connection()
            c = conn.cursor()
            c.execute("SELECT COUNT(*) as u_count FROM users WHERE role = 'resident'")
            u_count = c.fetchone()["u_count"]
            c.execute("SELECT COUNT(*) as s_count FROM sessions WHERE is_active = 1")
            s_count = c.fetchone()["s_count"]
            conn.close()

            stat_text = (
                f"📊 <b>XONADON+ TIZIM STATISTIKASI:</b>\n\n"
                f"👤 Ro‘yxatdan o‘tgan fuqarolar: <b>{u_count} ta</b>\n"
                f"📱 Faol seanslar (qurilmalar): <b>{s_count} ta</b>\n"
                f"🤖 Telegram bot obunachilari: <b>{len(subs)} ta</b>\n"
                f"📍 Pilot hudud: <b>Qashqadaryo, Nishon tumani, «Ko‘ksoy» MFY</b>"
            )
            send_message(chat_id, stat_text, parse_mode="HTML")
            return

        elif text == "⬅️ Asosiy menyuga qaytish" or text == "/exit_admin":
            user_sub.pop("admin_state", None)
            save_subscribers(subs)
            send_message(chat_id, "Asosiy menyuga qaytdingiz.", reply_markup=get_main_keyboard(chat_id))
            return

    # /start komandasi
    if text.startswith("/start"):
        handle_start(chat_id, user_info)
        return

    # 2. AGAR FOYDALANUVCHI SMS TASDIQLASH KODINI KUTISH BOSQICHIDA BO'LSA
    if user_sub.get("status") == "awaiting_otp":
        if text == "⬅️ Boshqa raqam kiritish":
            user_sub["status"] = "unverified"
            save_subscribers(subs)
            prompt = (
                "📱 Yangi telefon raqamingizni kiriting (Masalan: <code>+998940401009</code>) "
                "yoki pastdagi <b>«📱 Telefon raqamni ulashish»</b> tugmasini bosing:"
            )
            send_message(chat_id, prompt, reply_markup=get_contact_keyboard(), parse_mode="HTML")
            return

        expected_otp = user_sub.get("pending_otp", "7824")
        if text == expected_otp or text == "7824":
            # SMS kod to'g'ri kiritildi!
            verified_phone = user_sub.get("pending_phone", "+998 (94) 040-10-09")
            verified_raw = user_sub.get("pending_raw", "998940401009")

            user_sub["phone"] = verified_phone
            user_sub["raw_phone"] = verified_raw
            user_sub["phone_verified"] = True
            user_sub["status"] = "verified"
            user_sub["phone_verified_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            user_sub.pop("pending_otp", None)
            save_subscribers(subs)

            conf_text = (
                f"🎉 <b>TABRIKLAYMIZ! SMS KOD TASDIQLANDI!</b>\n\n"
                f"📱 <b>Tasdiqlangan telefon:</b> <code>{verified_phone}</code> ✅\n"
                f"🛡️ <b>Xavfsizlik:</b> SMS orqali to‘liq identifikatsiya qilindi\n"
                f"🔗 <b>Xonadon+ hisobi bilan bog‘landi:</b> Ha (Faol ✅)\n\n"
                f"📍 <b>Biriktirilgan manzil:</b>\n<i>{safe_html(user_sub['address']['street_label'])}</i>\n\n"
                f"🔔 Endi Isuzu gaz mashinasi ko‘changizga kirishi bilan sizga Telegram orqali avtomatik bildirishnoma yetib keladi.\n\n"
                f"Quyidagi menyudan foydalanishingiz mumkin 👇"
            )
            send_message(chat_id, conf_text, reply_markup=get_main_keyboard(chat_id), parse_mode="HTML")
            return
        else:
            send_message(
                chat_id,
                "❌ <b>Noto‘g‘ri tasdiqlash kodi!</b>\n\n"
                "Iltimos, yuborilgan 4 xonali SMS kodni to‘g‘ri kiriting (Demo kod: <code>7824</code>).\n"
                "Yoki raqamni almashtirish uchun «⬅️ Boshqa raqam kiritish» tugmasini bosing.",
                reply_markup=get_otp_keyboard(),
                parse_mode="HTML"
            )
            return

    # 3. AGAR TELEFON RAQAMI TASDIQLANMAGAN BO'LSA
    if not user_sub.get("phone_verified"):
        digits, formatted = normalize_phone(text)
        if digits:
            # Foydalanuvchi telefon raqamini matn sifatida yubordi -> SMS kod jo'natiladi!
            user_sub["pending_phone"] = formatted
            user_sub["pending_raw"] = digits
            user_sub["pending_otp"] = "7824"
            user_sub["status"] = "awaiting_otp"
            save_subscribers(subs)

            prompt_otp = (
                f"📩 <b>SMS TASDIQLASH KODI YUBORILDI!</b>\n\n"
                f"📱 <b>Raqam:</b> <code>{formatted}</code>\n"
                f"🔐 Begona shaxslar profilingizga ruxsatsiz kira olmasligi uchun ushbu raqamga 4 xonali tasdiqlash kodi yuborildi.\n\n"
                f"[🔔 <b>Demo rejimda SMS kod:</b> <code>7824</code>]\n\n"
                f"Iltimos, ushbu telefon raqami aynan sizga tegishli ekanligini tasdiqlash uchun 4 xonali kodni yozib yuboring (Masalan: <code>7824</code>):"
            )
            send_message(chat_id, prompt_otp, reply_markup=get_otp_keyboard(), parse_mode="HTML")
            return
        else:
            prompt_text = (
                "⚠️ <b>Diqqat:</b> Xonadon+ tizimidan foydalanish va gaz mashinasi bildirishnomalarini olish uchun "
                "avval telefon raqamingizni tasdiqlashingiz lozim.\n\n"
                "Iltimos, pastdagi <b>«📱 Telefon raqamni ulashish»</b> tugmasini bosing yoki telefon raqamingizni yozib yuboring (Masalan: <code>+998940401009</code>):"
            )
            send_message(chat_id, prompt_text, reply_markup=get_contact_keyboard(), parse_mode="HTML")
            return

    # 4. TASDIQLANGAN FOYDALANUVCHILAR UCHUN MENYU KOMANDALARI

    # Agar foydalanuvchi manzil tanlash bosqichida matn yozsa -> Faqat tugmalardan tanlashini so'raymiz
    if user_sub.get("status") == "awaiting_address" and text and not text.startswith("/") and not text.startswith("⬅️"):
        warn_msg = (
            "⚠️ <b>Manzil faqat bot tugmalari orqali tanlanadi!</b>\n\n"
            "Tizimda yo‘q manzillar kiritilishi va gaz yetkazib berishda xatoliklar kelib chiqishining oldini olish uchun, "
            "iltimos, viloyat, tuman, mahalla va ko‘changizni <b>pastdagi tugmalar</b> orqali ketma-ket tanlang 👇"
        )
        send_message(chat_id, warn_msg, reply_markup=get_region_keyboard(), parse_mode="HTML")
        return

    # Manzilni biriktirish / Manzilni o'zgartirish (Faqat tugmalar orqali ketma-ket tanlash)
    if text in ["📍 Manzilimni biriktirish", "✏️ Manzilni o‘zgartirish", "/manzil"]:
        user_sub["status"] = "awaiting_address"
        save_subscribers(subs)
        curr_addr = user_sub.get("address_text") or user_sub.get("address", {}).get("street_label", "")
        curr_info = f"\n\n📌 <b>Amaldagi manzil:</b> <i>{safe_html(curr_addr)}</i>" if curr_addr else ""
        prompt = (
            f"📍 <b>Xonadon manzilingizni tanlang:</b>{curr_info}\n\n"
            f"Tizimdagi aniq manzilingizni belgilash uchun, avval <b>viloyatingizni</b> tanlang:"
        )
        send_message(chat_id, prompt, reply_markup=get_region_keyboard(), parse_mode="HTML")
        return

    # Gaz mashinasi qayerda? / Haydovchi qayerda?
    if text in ["🚚 Gaz mashinasi qayerda?", "🚚 Haydovchi qayerda?", "Haydovchi qayerda?", "Haydovchi qayerda", "/mashina", "/haydovchi"] or (text and "qayerda" in text.lower() and ("gaz" in text.lower() or "mashina" in text.lower() or "haydovchi" in text.lower())):
        u_addr = safe_html(user_sub.get("address", {}).get("street_label", "Istiqlol ko‘chasi"))
        truck_addr = safe_html(current_driver_state['last_address_text'])
        is_collect = (current_driver_state["stage"] == "collect")
        stage_text = "🟢 1-bosqich: Bo‘sh balonlarni yig‘ish" if is_collect else "🔵 2-bosqich: To‘ldirilgan balonlarni tarqatish"

        user_street_key = user_sub.get("address", {}).get("street")
        driver_street_key = current_driver_state.get("street")
        is_same_street = (user_street_key and driver_street_key and user_street_key == driver_street_key)

        is_waiting = (current_driver_state.get("status") in ["waiting", "on_the_way"])

        if is_waiting:
            status_text = (
                "🚚 <b>GAZ MASHINASI JORIY HOLATI</b>\n\n"
                "⏸️ <b>Mashina hozirda kutish rejimida!</b>\n\n"
                "Haydovchi hozirda navbat kutish yoki qisqa tanaffus holatida. "
                "Mashina ko‘changizga yoki mahallangizga xizmat ko‘rsatishni boshlagan zahoti sizga avtomatik xabar yetib boradi."
            )
            send_message(chat_id, status_text, parse_mode="HTML")
            return
        else:
            # Ko'chaga kirilgan holati
            if is_same_street:
                current_state_badge = (
                    "🟢 <b>JORIY HOLAT: MASHINA SIZNING KO‘CHANGIZDA!</b>\n"
                    "🚗 <i>Haydovchi hozirda sizning ko‘changizdagi xonadonlarga xizmat ko‘rsatmoqda!</i>"
                )
            else:
                current_state_badge = (
                    f"🟡 <b>JORIY HOLAT: Mashina hozirda boshqa ko‘chada (xizmat ko‘rsatilmoqda):</b>\n"
                    f"👉 <b>{truck_addr}</b>\n\n"
                    f"🏠 <i>Sizning manzilingiz: {u_addr}</i>\n"
                    f"⏳ <i>Mashina navbat bilan sizning ko‘changizga ham yetib keladi.</i>"
                )

        t_model = current_driver_state.get("truck_model") or "Isuzu NPR 75"
        t_plate = current_driver_state.get("truck_plate") or "30 782 AGA"
        t_color = current_driver_state.get("truck_color") or "Oq (Sariq chiziqli)"

        status_text = (
            f"🚚 <b>GAZ MASHINASI HARAKATI VA JORIY HOLATI</b>\n\n"
            f"{current_state_badge}\n\n"
            f"📍 <b>Yo‘nalish manzili:</b> <b>{truck_addr}</b>\n"
            f"📌 <b>Harakat bosqichi:</b> <b>{stage_text}</b>\n"
            f"🚛 <b>Maxsus mashina:</b> {safe_html(t_model)} (<code>{safe_html(t_plate)}</code>)\n"
            f"🎨 <b>Mashina rangi:</b> {safe_html(t_color)}\n"
            f"👨‍✈️ <b>Haydovchi:</b> <b>{safe_html(current_driver_state['driver_name'])}</b>\n"
            f"📞 <b>Haydovchi telefoni:</b> <code>{safe_html(current_driver_state['driver_phone'])}</code>\n"
            f"💰 <b>Balon narxi (Davlat tarifi):</b> <b>20 000 so‘m</b>\n"
            f"⏱ <b>Vaqt:</b> {safe_html(current_driver_state['last_alert_time'] or 'Hozirgina yo‘lga chiqdi')}\n"
            f"🟢 <b>GPS holati:</b> Jonli uzatilmoqda"
        )
        send_message(chat_id, status_text, parse_mode="HTML")
        return

    # Balon uchun to'lov
    if text == "💳 Balon uchun to‘lov" or text == "/tolov":
        pay_text = (
            "💳 <b>GAZ BALONI UCHUN TO‘LOV (DAVLAT TARIFI)</b>\n\n"
            "1 dona to‘ldirilgan suyultirilgan gaz baloni narxi: <b>20 000 so‘m</b>\n"
            "Provayder: <b>«Hududgaz Pastdarg‘om» / «Hududgazta’minot» AJ</b>\n\n"
            "To‘lov usullari:\n"
            "1️⃣ <b>Xonadon+ Platinum Kartasi</b> (+2% keshbek)\n"
            "2️⃣ <b>Uzcard / Humo</b> orqali bir zumda to‘lash\n\n"
            "Xonadon+ ilovasi orqali to‘lovni amalga oshirish uchun pastdagi tugmani bosing 👇"
        )
        kb = {
            "inline_keyboard": [
                [{"text": "💳 Onlayn to‘lash ma’lumotlari", "callback_data": "pay_lpg_now"}],
                [{"text": "📞 Dispetcher bilan bog‘lanish", "callback_data": "call_driver"}]
            ]
        }
        send_message(chat_id, pay_text, reply_markup=kb, parse_mode="HTML")
        return

    # Xavfsizlik qoidalari
    if text == "🛡️ Xavfsizlik qoidalari" or text == "/xavfsizlik":
        safety_text = (
            "🛡️ <b>SUYULTIRILGAN GAZ BALONIDAN XAVFSIZ FOYDALANISH QOIDALARI:</b>\n\n"
            "1️⃣ <b>Issiqlikdan saqlang:</b> Gaz balonini pech yoki isitish moslamalaridan kamida 1 metr masofada saqlang.\n"
            "2️⃣ <b>Shamollatish:</b> Gaz ballonlari faqat shamollatish tizimi mavjud bo‘lgan xonalarga o‘rnatilishi lozim.\n"
            "3️⃣ <b>Sovun ko‘pigi bilan tekshiring:</b> Gaz sizib chiqishini tekshirish uchun faqat sovun ko‘pigidan foydalaning. <b>Aslo ochiq olov yoki gugurt yoqmang!</b>\n"
            "4️⃣ <b>Bolalardan saqlang:</b> Gaz jo‘mragini foydalanib bo‘lgach doimo yopib qo‘ying.\n"
            "5️⃣ <b>Favqulodda holatda:</b> Gaz hidi sezilsa, darhol xonani shamollating va <b>104</b> gaz avariya xizmatiga qo‘ng‘iroq qiling!"
        )
        send_message(chat_id, safety_text, parse_mode="HTML")
        return

    # Foydalanuvchi profili va telefon raqam
    if text == "👤 Profilim va Telefon raqam" or text == "/profil" or text == "/telefon":
        phone_val = safe_html(user_sub.get("phone", "+998 (94) 040-10-09"))
        addr_val = safe_html(user_sub.get("address", {}).get("street_label", "Belgilanmagan"))
        first_n = safe_html(user_sub.get("first_name", user_info.get("first_name", "Fuqaro")))
        uname = user_sub.get("username", user_info.get("username", ""))
        uname_str = f"@{uname}" if uname else "Mavjud emas"

        profile_text = (
            f"👤 <b>FOYDALANUVCHI SHAXSIY PROFILI</b>\n\n"
            f"📱 <b>Tasdiqlangan telefon:</b> <code>{phone_val}</code> ✅\n"
            f"👤 <b>Ism:</b> {first_n}\n"
            f"💬 <b>Telegram:</b> <code>{safe_html(uname_str)}</code>\n"
            f"🆔 <b>Telegram ID:</b> <code>{chat_id}</code>\n\n"
            f"📍 <b>Biriktirilgan manzil:</b>\n<i>{addr_val}</i>\n\n"
            f"🔗 <b>Xonadon+ Veb-ilovasi bilan integratsiya:</b> 🟢 Bog‘langan (Sinxronlangan)\n"
            f"🛡️ <b>Xavfsizlik darajasi:</b> Yuqori (SMS / Kontakt tasdiqlangan)\n"
            f"🔔 <b>Gaz mashinasi ogohlantirishlari:</b> 🟢 Faol"
        )
        kb = {
            "inline_keyboard": [
                [{"text": "🔄 Telefon raqamni o‘zgartirish", "callback_data": "change_phone"}],
                [{"text": "📍 Manzilni o‘zgartirish", "callback_data": "back_to_reg"}]
            ]
        }
        send_message(chat_id, profile_text, reply_markup=kb, parse_mode="HTML")
        return

    # Default javob
    send_message(
        chat_id,
        "Iltimos, quyidagi menyudan kerakli bo‘limni tanlang 👇",
        reply_markup=get_main_keyboard(chat_id),
        parse_mode="HTML"
    )

# ========================================================
# 7. INLINE TUGMALARNI QAYTA ISHLASH (CALLBACK QUERIES)
# ========================================================
def handle_callback(cb):
    cb_id = cb["id"]
    data = cb.get("data", "")
    msg = cb.get("message", {})
    chat_id = msg.get("chat", {}).get("id")
    msg_id = msg.get("message_id")

    answer_callback(cb_id)

    # --- HAYDOVCHINI O'CHIRISH CALLBACKLARI ---
    if data.startswith("deldriver_"):
        phone_to_del = data.split("deldriver_")[1].strip()
        confirm_text = (
            f"⚠️ <b>HAYDOVCHINI O‘CHIRISHNI TASDIQLANG:</b>\n\n"
            f"📱 <b>Telefon/Login:</b> <code>{safe_html(phone_to_del)}</code>\n\n"
            f"Haqiqatan ham ushbu haydovchini tizimdan butunlay o‘chirib tashlamoqchimisiz?\n"
            f"<i>(O‘chirilgach, ushbu haydovchi qaytib ilovaga kira olmaydi)</i>"
        )
        inline_confirm = {
            "inline_keyboard": [
                [{"text": "🗑 Ha, butunlay o‘chirish", "callback_data": f"confdel_{phone_to_del}"}],
                [{"text": "❌ Bekor qilish", "callback_data": "cancel_del"}]
            ]
        }
        send_message(chat_id, confirm_text, reply_markup=inline_confirm, parse_mode="HTML")
        return

    if data.startswith("confdel_"):
        phone_to_del = data.split("confdel_")[1].strip()
        db_manager.delete_driver(phone_to_del)
        clean_del = re.sub(r'\D', '', str(phone_to_del))
        clean_cur = re.sub(r'\D', '', str(current_driver_state.get('driver_phone', '')))
        if clean_del and clean_cur and clean_del[-9:] == clean_cur[-9:]:
            current_driver_state['status'] = 'waiting'
            current_driver_state['is_active'] = 0
        edit_message_text(
            chat_id, msg_id,
            f"✅ <b>Haydovchi ({safe_html(phone_to_del)}) tizimdan butunlay o‘chirildi!</b>\nUning hisobi va kirish ruxsatnomasi bekor qilindi.",
            parse_mode="HTML"
        )
        return

    if data == "cancel_del":
        edit_message_text(
            chat_id, msg_id,
            "❌ <b>Haydovchini o‘chirish bekor qilindi.</b>",
            parse_mode="HTML"
        )
        return

    # --- HAYDOVCHINI O'CHIRISH CALLBACKLARI ---
    if data.startswith("deldriver_"):
        phone_to_del = data.split("deldriver_")[1].strip()
        confirm_text = (
            f"⚠️ <b>HAYDOVCHINI O‘CHIRISHNI TASDIQLANG:</b>\n\n"
            f"📱 <b>Telefon/Login:</b> <code>{safe_html(phone_to_del)}</code>\n\n"
            f"Haqiqatan ham ushbu haydovchini tizimdan butunlay o‘chirib tashlamoqchimisiz?\n"
            f"<i>(O‘chirilgach, ushbu haydovchi qaytib ilovaga kira olmaydi)</i>"
        )
        inline_confirm = {
            "inline_keyboard": [
                [{"text": "🗑 Ha, butunlay o‘chirish", "callback_data": f"confdel_{phone_to_del}"}],
                [{"text": "❌ Bekor qilish", "callback_data": "cancel_del"}]
            ]
        }
        send_message(chat_id, confirm_text, reply_markup=inline_confirm, parse_mode="HTML")
        return

    if data.startswith("confdel_"):
        phone_to_del = data.split("confdel_")[1].strip()
        db_manager.delete_driver(phone_to_del)
        clean_del = re.sub(r'\D', '', str(phone_to_del))
        clean_cur = re.sub(r'\D', '', str(current_driver_state.get('driver_phone', '')))
        if clean_del and clean_cur and clean_del[-9:] == clean_cur[-9:]:
            current_driver_state['status'] = 'waiting'
            current_driver_state['is_active'] = 0
        edit_message_text(
            chat_id, msg_id,
            f"✅ <b>Haydovchi ({safe_html(phone_to_del)}) tizimdan butunlay o‘chirildi!</b>\nUning hisobi va kirish ruxsatnomasi bekor qilindi.",
            parse_mode="HTML"
        )
        return

    if data == "cancel_del":
        edit_message_text(
            chat_id, msg_id,
            "❌ <b>Haydovchini o‘chirish bekor qilindi.</b>",
            parse_mode="HTML"
        )
        return

    # Telefon raqamni o'zgartirish
    if data == "change_phone":
        subs = load_subscribers()
        cid_str = str(chat_id)
        if cid_str in subs:
            subs[cid_str]["phone_verified"] = False
            subs[cid_str]["status"] = "unverified"
            save_subscribers(subs)
        send_message(
            chat_id,
            "📱 Yangi telefon raqamingizni tasdiqlash uchun pastdagi <b>«📱 Telefon raqamni ulashish»</b> tugmasini bosing yoki raqamingizni yozib yuboring (Masalan: <code>+998940401009</code>):",
            reply_markup=get_contact_keyboard(),
            parse_mode="HTML"
        )
        return

    # 1. Ortga qaytish
    if data == "back_to_reg":
        edit_message_text(
            chat_id, msg_id,
            "📍 <b>Viloyatingizni tanlang:</b>",
            reply_markup=get_region_keyboard(),
            parse_mode="HTML"
        )
        return

    # 2. Viloyat tanlandi -> Tumanlar
    if data.startswith("reg:"):
        reg_key = data.split(":")[1]
        reg_name = ADDRESS_DB.get(reg_key, {}).get("name", "Viloyat")
        edit_message_text(
            chat_id, msg_id,
            f"📍 Tanlangan viloyat: <b>{safe_html(reg_name)}</b>\n\nEndi <b>tumaningizni</b> tanlang:",
            reply_markup=get_district_keyboard(reg_key),
            parse_mode="HTML"
        )
        return

    # 3. Tuman tanlandi -> MFYlar
    if data.startswith("dist:"):
        parts = data.split(":")
        reg_key, dist_key = parts[1], parts[2]
        dist_name = ADDRESS_DB.get(reg_key, {}).get("districts", {}).get(dist_key, {}).get("name", "Tuman")
        edit_message_text(
            chat_id, msg_id,
            f"🏛 Tanlangan tuman: <b>{safe_html(dist_name)}</b>\n\nEndi <b>MFY (mahalla)</b>ingizni tanlang:",
            reply_markup=get_mfy_keyboard(reg_key, dist_key),
            parse_mode="HTML"
        )
        return

    # 4. MFY tanlandi -> Ko'chalar
    if data.startswith("mfy:"):
        parts = data.split(":")
        reg_key, dist_key, mfy_key = parts[1], parts[2], parts[3]
        mfy_name = ADDRESS_DB.get(reg_key, {}).get("districts", {}).get(dist_key, {}).get("mfys", {}).get(mfy_key, {}).get("name", "MFY")
        edit_message_text(
            chat_id, msg_id,
            f"🏡 Tanlangan MFY: <b>{safe_html(mfy_name)}</b>\n\nEndi <b>ko‘changizni</b> tanlang:",
            reply_markup=get_street_keyboard(reg_key, dist_key, mfy_key),
            parse_mode="HTML"
        )
        return

    # 5. Ko'cha tanlandi -> Saqlash!
    if data.startswith("st:"):
        parts = data.split(":")
        reg_key, dist_key, mfy_key, street_key = parts[1], parts[2], parts[3], parts[4]

        reg_name = ADDRESS_DB[reg_key]["name"]
        dist_name = ADDRESS_DB[reg_key]["districts"][dist_key]["name"]
        mfy_name = ADDRESS_DB[reg_key]["districts"][dist_key]["mfys"][mfy_key]["name"]
        street_name = ADDRESS_DB[reg_key]["districts"][dist_key]["mfys"][mfy_key]["streets"][street_key]

        full_addr = f"{reg_name}, {dist_name}, {mfy_name}, {street_name}"

        subs = load_subscribers()
        cid_str = str(chat_id)
        if cid_str not in subs:
            subs[cid_str] = {"chat_id": chat_id}

        subs[cid_str]["address"] = {
            "region": reg_key,
            "district": dist_key,
            "mfy": mfy_key,
            "street": street_key,
            "street_label": full_addr
        }
        save_subscribers(subs)

        success_text = (
            f"🎉 <b>MANZILINGIZ MUVAFFAQIYATLI SAQLANDI!</b>\n\n"
            f"📍 <b>{safe_html(full_addr)}</b>\n\n"
            f"Endi gaz mashinasi aynan shu ko‘chaga kirganida sizga avtomatik tarzda "
            f"Telegram orqali bildirishnoma yuboriladi.\n\n"
            f"Rahmat! Siz Xonadon+ tizimiga muvaffaqiyatli ulandingiz."
        )
        edit_message_text(chat_id, msg_id, success_text, parse_mode="HTML")
        send_message(chat_id, "Asosiy menyuga xush kelibsiz! Kerakli xizmatni tanlang:", reply_markup=get_main_keyboard(chat_id))
        return

    if data == "pay_lpg_now":
        pay_info = (
            "💳 <b>Gaz baloni uchun to‘lov (20 000 so‘m)</b>\n\n"
            "To‘lovni Xonadon+ veb-ilovasida yoki Xonadon Platinum kartangiz orqali amalga oshirishingiz mumkin:\n"
            "👉 http://localhost:3000\n\n"
            "Kvitansiya avtomatik ravishda haydovchining planshetiga boradi."
        )
        send_message(chat_id, pay_info, parse_mode="HTML")
        return

    if data == "show_safety":
        send_message(chat_id, "🛡️ Gaz sizib chiqishini faqat sovun ko‘pigi bilan tekshiring! Aslo ochiq olov yoqmang.", parse_mode="HTML")
        return

    if data == "call_driver":
        t_model = current_driver_state.get("truck_model") or "Isuzu NPR 75"
        t_plate = current_driver_state.get("truck_plate") or "30 782 AGA"
        t_color = current_driver_state.get("truck_color") or "Oq (Sariq chiziqli)"
        contact_info = (
            "📞 <b>HAYDOVCHI VA DISPETCHERLIK ALOQASI</b>\n\n"
            f"👨‍✈️ <b>Haydovchi:</b> {safe_html(current_driver_state['driver_name'])}\n"
            f"📱 <b>Haydovchi telefoni:</b> <code>{safe_html(current_driver_state['driver_phone'])}</code>\n"
            f"🚛 <b>Maxsus mashina:</b> {safe_html(t_model)} (<code>{safe_html(t_plate)}</code>)\n"
            f"🎨 <b>Rangi:</b> {safe_html(t_color)}\n\n"
            "🏢 <b>24/7 Dispetcherlik markazi:</b>\n"
            "📞 Telefon: <code>+998 (71) 200-00-44</code>\n"
            "📍 Gaz ta’minoti filiali: <b>Pastdarg‘om / Nishon bo‘limi</b>"
        )
        send_message(chat_id, contact_info, parse_mode="HTML")
        return

# ========================================================
# 8. LOCAL HTTP SERVER (WEB ILOVA BILAN ALOQA)
# ========================================================
class AlertApiHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_GET(self):
        
        # --- SERVE AVATAR IMAGES ---
        if self.path.startswith("/uploads/avatars/"):
            filename = os.path.basename(self.path.split("?")[0])
            filepath = os.path.join(BASE_DIR, "uploads", "avatars", filename)
            if os.path.exists(filepath):
                self.send_response(200)
                content_type = "image/png" if filename.lower().endswith(".png") else "image/jpeg"
                self.send_header("Content-Type", content_type)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                with open(filepath, "rb") as f:
                    self.wfile.write(f.read())
                return
            else:
                self.send_response(404)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                return

        # --- REAL-TIME ACTIVE TRUCKS FOR CITIZEN MAP & CARDS ---
        if self.path.startswith("/api/active-trucks") or self.path.startswith("/api/get-active-trucks"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            qs = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(qs)
            q_reg = params.get("region", ["qashqadaryo"])[0]
            q_dist = params.get("district", ["nishon"])[0]
            q_mfy = params.get("mfy", ["yangi_nishon"])[0]

            db_trucks = db_manager.get_active_trucks(region=q_reg, district=q_dist, mfy=q_mfy)

            drv_phone = current_driver_state.get("driver_phone", "")
            is_waiting = (current_driver_state.get("status") in ["waiting", "idle"])
            is_active_flag = current_driver_state.get("is_active", 1)
            is_match_mfy = (not q_mfy or current_driver_state.get("mfy") == q_mfy)
            is_match_dist = (not q_dist or current_driver_state.get("district") == q_dist)

            db_driver = db_manager.get_driver_by_phone(drv_phone) if drv_phone else None

            response_trucks = []
            seen_plates = set()

            if not is_waiting and is_active_flag and is_match_mfy and is_match_dist and db_driver:
                clean_phone_id = re.sub(r'\D', '', str(drv_phone))[-7:]
                live_truck = {
                    "id": f"drv_{clean_phone_id}",
                    "name": current_driver_state.get("driver_name", "Ahror Suyunov"),
                    "phone": drv_phone,
                    "model": current_driver_state.get("truck_model", "Isuzu NPR 75"),
                    "plate": current_driver_state.get("truck_plate", "70 M 260 EB"),
                    "color": current_driver_state.get("truck_color", "Oq (Sariq chiziqli)"),
                    "status": current_driver_state.get("status", "arrived"),
                    "street": current_driver_state.get("street", "istiqlol"),
                    "street_name": current_driver_state.get("street_name", "Istiqlol ko‘chasi"),
                    "mfy": current_driver_state.get("mfy", q_mfy),
                    "district": current_driver_state.get("district", q_dist),
                    "region": current_driver_state.get("region", q_reg),
                    "lat": 38.6850,
                    "lng": 65.6800,
                    "avatar_url": current_driver_state.get("avatar_url") or (db_driver.get("avatar_url") if db_driver else "") or ""
                }
                response_trucks.append(live_truck)
                seen_plates.add(live_truck["plate"].replace(" ", "").upper())

            for dt in db_trucks:
                pl_clean = dt.get("truck_plate", "").replace(" ", "").upper()
                if pl_clean not in seen_plates:
                    dt_phone_clean = re.sub(r'\D', '', str(dt.get('phone', '')))[-7:]
                    response_trucks.append({
                        "id": f"drv_{dt_phone_clean}",
                        "name": dt.get("full_name", ""),
                        "phone": dt.get("phone", ""),
                        "model": dt.get("truck_model", "Isuzu NPR 75"),
                        "plate": dt.get("truck_plate", ""),
                        "color": dt.get("truck_color", "Oq"),
                        "status": dt.get("status", "arrived"),
                        "street": dt.get("street", "istiqlol"),
                        "street_name": dt.get("street_name", "Istiqlol ko‘chasi"),
                        "mfy": dt.get("assigned_mfy", q_mfy),
                        "district": dt.get("assigned_district", q_dist),
                        "region": dt.get("assigned_region", q_reg),
                        "lat": dt.get("lat", 38.6850),
                        "lng": dt.get("lng", 65.6800),
                        "avatar_url": dt.get("avatar_url", "")
                    })
                    seen_plates.add(pl_clean)

            self.wfile.write(json.dumps({"status": "ok", "trucks": response_trucks}).encode("utf-8"))
            return

        if self.path.startswith("/api/app-version"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            version_info = {
                "latest_version": "1.0.1",
                "version_code": 101,
                "release_date": "2026-10-16",
                "download_url": "https://github.com/ahrorbek0005/xonadon-plus-server/raw/main/XonadonPlus.apk",
                "changelog": [
                    "Xaritadagi mashina axborot kartochkasi xarita ustidan tashqariga chiqarildi va qulaylashtirildi",
                    "To‘liq ishlovchi QR-kod skaneri: real kamera, fonar (chiroq) va galereyadan rasm tanlash",
                    "Onlayn versiya tekshirish va yangilanish tizimi qo‘shildi"
                ]
            }
            self.wfile.write(json.dumps(version_info).encode("utf-8"))
            return

        if self.path.startswith("/api/driver/location"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            loc = db_manager.get_driver_location("koksoy")
            self.wfile.write(json.dumps({"driver": loc or {"lat": 38.665, "lng": 65.698, "status": "arrived"}}).encode("utf-8"))
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        subs = load_subscribers()
        resp = {
            "status": "online",
            "bot_username": "xonadon_plus_bot",
            "subscribers_count": len(subs),
            "driver_state": current_driver_state,
            "subscribers": subs
        }
        self.wfile.write(json.dumps(resp).encode("utf-8"))

    def do_POST(self):

        # --- API: 2FA FORGOT RECOVERY REQUEST (SEND 6-CHAR ALPHANUMERIC CODE TO BOT) ---
        
        # --- API: UPLOAD PROFILE AVATAR (DRIVER & RESIDENT) ---
        if self.path == "/api/upload-avatar":
            try:
                import base64
                length = int(self.headers.get("Content-Length", 0) or 0)
                body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
                data = json.loads(body)
                phone = str(data.get("phone", "")).strip()
                role = str(data.get("role", "resident")).strip()
                image_data = data.get("image_data", "")

                avatar_url = ""
                if image_data:
                    clean_p = re.sub(r'\D', '', phone) or "user"
                    uploads_dir = os.path.join(BASE_DIR, "uploads", "avatars")
                    os.makedirs(uploads_dir, exist_ok=True)
                    filename = f"avatar_{clean_p}_{int(time.time())}.jpg"
                    filepath = os.path.join(uploads_dir, filename)

                    if "," in image_data:
                        header, encoded = image_data.split(",", 1)
                    else:
                        encoded = image_data
                    try:
                        with open(filepath, "wb") as f:
                            f.write(base64.b64decode(encoded))
                        avatar_url = f"/uploads/avatars/{filename}"
                    except Exception as err:
                        print("Avatar file write failed, using data URL:", err)
                        avatar_url = image_data

                db_manager.save_user_avatar(phone, role, avatar_url or image_data)
                if role == "driver":
                    current_driver_state["avatar_url"] = avatar_url or image_data

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok", "avatar_url": avatar_url or image_data}).encode("utf-8"))
                return
            except Exception as e:
                print("Error in /api/upload-avatar:", e)
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
                return

        if self.path == "/api/auth/2fa-forgot-request":
            try:
                import random, string
                length = int(self.headers.get("Content-Length", 0) or 0)
                body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
                data = json.loads(body)
                phone = str(data.get("phone", "")).strip()
                raw_phone = re.sub(r'\D', '', phone)

                subs = load_subscribers()
                target_chat_id = None
                for cid, s in subs.items():
                    s_phone = re.sub(r'\D', '', str(s.get("phone", "") or s.get("raw_phone", "")))
                    if s_phone and (s_phone == raw_phone or s_phone.endswith(raw_phone[-9:]) or raw_phone.endswith(s_phone[-9:])):
                        target_chat_id = s.get("chat_id") or cid
                        break

                if not target_chat_id:
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "ok": False,
                        "message": "Ushbu telefon raqam Telegram botimizga ulanmagan. Iltimos, Telegramda @xonadon_plus_bot ga kirib /start bosing."
                    }).encode("utf-8"))
                    return

                # 6-character random alphanumeric code (uppercase letters + numbers)
                chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
                recovery_code = "".join(random.choice(chars) for _ in range(6))
                db_manager.set_otp(raw_phone + "_2fa_reset", recovery_code, expire_secs=600)

                msg = (
                    "🔐 <b>Xonadon+ 2FA Parolini Tiklash</b>\n\n"
                    "Ikki bosqichli maxfiy parolingizni tiklash uchun 6 xonali maxsus kodingiz:\n"
                    f"🔑 <code>{recovery_code}</code>\n\n"
                    "⚠️ <i>Xavfsizlik eslatmasi: Ushbu kodni hech kimga bermang! Kod 10 daqiqa davomida amal qiladi.</i>"
                )
                send_message(target_chat_id, msg, parse_mode="HTML")

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "ok": True,
                    "message": "Maxsus 4 xonali tiklash kodi Telegram botingizga yuborildi!"
                }).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode("utf-8"))
            return

        # --- API: 2FA FORGOT RECOVERY VERIFY ---
        if self.path == "/api/auth/2fa-forgot-verify":
            try:
                length = int(self.headers.get("Content-Length", 0) or 0)
                body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
                data = json.loads(body)
                phone = str(data.get("phone", "")).strip()
                code = str(data.get("code", "")).strip().upper()
                raw_phone = re.sub(r'\D', '', phone)

                is_valid = db_manager.verify_otp(raw_phone + "_2fa_reset", code)
                if not is_valid:
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "ok": False,
                        "message": "❌ Tiklash kodi noto‘g‘ri yoki muddati o‘tgan!"
                    }).encode("utf-8"))
                    return

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "ok": True,
                    "message": "Kod tasdiqlandi. Endi yangi 2FA parol o‘rnatishingiz mumkin."
                }).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode("utf-8"))
            return


        # --- API: SEND SMS CODE DIRECTLY TO LINKED TELEGRAM BOT CHAT ---
                # Check if phone number is already registered
        if self.path.startswith("/api/auth/check-user"):
            try:
                import urllib.parse
                qs = urllib.parse.urlparse(self.path).query
                params = urllib.parse.parse_qs(qs)
                phone = params.get("phone", [""])[0]
                raw_p = re.sub(r'\D', '', phone)
                last9 = raw_p[-9:] if len(raw_p) >= 9 else raw_p

                conn = db_manager.get_connection()
                c = conn.cursor()
                c.execute("SELECT * FROM users WHERE phone LIKE ?", (f"%{last9}%",))
                u = c.fetchone()
                if not u:
                    c.execute("SELECT * FROM drivers WHERE phone LIKE ?", (f"%{last9}%",))
                    u = c.fetchone()
                conn.close()

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "exists": bool(u)}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode("utf-8"))
            return

        if self.path == "/api/auth/send-sms-code":
            try:
                import random
                length = int(self.headers.get("Content-Length", 0) or 0)
                body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
                data = json.loads(body)
                phone = str(data.get("phone", "")).strip()
                action = data.get("action", "login") # 'login' or 'register'
                raw_phone = re.sub(r'\D', '', phone)

                if len(raw_phone) < 9:
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(json.dumps({"ok": False, "message": "Telefon raqam noto‘g‘ri!"}).encode("utf-8"))
                    return

                # If action is login, check if user exists in database
                if action == "login":
                    user = db_manager.get_user_by_phone(f"+{raw_phone}") or db_manager.get_user_by_phone(raw_phone)
                    if not user:
                        conn = db_manager.get_connection()
                        c = conn.cursor()
                        c.execute("SELECT * FROM users WHERE phone LIKE ?", (f"%{raw_phone[-9:]}%",))
                        user = c.fetchone()
                        conn.close()

                    if not user:
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.end_headers()
                        self.wfile.write(json.dumps({
                            "ok": False,
                            "not_registered": True,
                            "message": "❌ Bu telefon raqam tizimda ro‘yxatdan o‘tmagan! Iltimos, avval «Ro‘yxatdan o‘tish» bo‘limiga o‘ting."
                        }).encode("utf-8"))
                        return
                
                # If action is register, prevent registering an already registered phone
                elif action == "register":
                    conn = db_manager.get_connection()
                    c = conn.cursor()
                    c.execute("SELECT * FROM users WHERE phone LIKE ?", (f"%{raw_phone[-9:]}%",))
                    existing_user = c.fetchone()
                    if not existing_user:
                        c.execute("SELECT * FROM drivers WHERE phone LIKE ?", (f"%{raw_phone[-9:]}%",))
                        existing_user = c.fetchone()
                    conn.close()

                    if existing_user:
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.end_headers()
                        self.wfile.write(json.dumps({
                            "ok": False,
                            "already_registered": True,
                            "message": "❌ Ushbu telefon raqam allaqachon ro‘yxatdan o‘tgan! Iltimos, «Kirish» bo‘limiga o‘ting."
                        }).encode("utf-8"))
                        return

                # Check if phone is linked to Telegram bot
                subs = load_subscribers()
                target_chat_id = None
                target_sub = None

                for cid, s in subs.items():
                    s_phone = re.sub(r'\D', '', str(s.get("phone", "") or s.get("raw_phone", "")))
                    if s_phone and (s_phone == raw_phone or s_phone.endswith(raw_phone[-9:]) or raw_phone.endswith(s_phone[-9:])):
                        target_chat_id = s.get("chat_id") or cid
                        target_sub = s
                        break

                if not target_chat_id:
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "ok": False,
                        "bot_linked": False,
                        "message": "⚠️ Ushbu telefon raqam Telegram botimizga hali ulanmagan!\n\nIltimos, Telegramda @xonadon_plus_bot ga kiring, /start bosing va telefon raqamingizni yuboring."
                    }).encode("utf-8"))
                    return

                # Generate 4-digit code
                code = f"{random.randint(1000, 9999)}"
                db_manager.set_otp(raw_phone, code)

                # Send directly to this specific user's chat_id!
                msg = (
                    "🔥 <b>Xonadon+ Xavfsizlik Xizmati</b>\n\n"
                    "Ilovaga kirish/ro‘yxatdan o‘tish uchun 4 xonali SMS kodingiz:\n"
                    f"🔢 <code>{code}</code>\n\n"
                    "⚠️ <i>Kodni hech kimga bermang! Kod 5 daqiqa davomida amal qiladi.</i>"
                )
                send_message(target_chat_id, msg, parse_mode="HTML")

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "ok": True,
                    "phone": phone,
                    "chat_id": target_chat_id,
                    "message": "SMS kod Telegram botingizga yuborildi!"
                }).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode("utf-8"))
            return

        # --- API: VERIFY SMS CODE ---
        if self.path == "/api/auth/verify-sms-code":
            try:
                length = int(self.headers.get("Content-Length", 0) or 0)
                body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
                data = json.loads(body)
                phone = str(data.get("phone", "")).strip()
                code = str(data.get("code", "")).strip()
                action = data.get("action", "login")
                reg_data = data.get("register_data", {})
                raw_phone = re.sub(r'\D', '', phone)

                # Verify code
                is_valid = db_manager.verify_otp(raw_phone, code)
                if not is_valid:
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "ok": False,
                        "message": "❌ Kiritilgan SMS kod noto‘g‘ri yoki muddati o‘tgan!"
                    }).encode("utf-8"))
                    return

                if action == "register":
                    fn = reg_data.get("first_name", "").strip()
                    ln = reg_data.get("last_name", "").strip()
                    full_name = f"{fn} {ln}".strip() or "Ahror Suyunov"
                    res = db_manager.register_user(
                        phone=f"+{raw_phone}",
                        full_name=full_name,
                        role="resident",
                        region="qashqadaryo",
                        district="nishon",
                        mfy="koksoy",
                        street="koksoy_markaziy",
                        house_number="1-uy"
                    )
                    user_obj = res.get("user")
                    if not user_obj:
                        user_obj = {"phone": f"+{raw_phone}", "full_name": full_name, "role": "resident", "account_id": db_manager.generate_unique_account_id("XP-")}
                    elif not user_obj.get("account_id"):
                        user_obj["account_id"] = db_manager.generate_unique_account_id("XP-")

                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "ok": True,
                        "action": "register",
                        "user": user_obj
                    }).encode("utf-8"))
                    return
                else:
                    # Login
                    user = db_manager.get_user_by_phone(f"+{raw_phone}") or db_manager.get_user_by_phone(raw_phone)
                    if not user:
                        conn = db_manager.get_connection()
                        c = conn.cursor()
                        c.execute("SELECT * FROM users WHERE phone LIKE ?", (f"%{raw_phone[-9:]}%",))
                        user = c.fetchone()
                        conn.close()
                    user_dict = dict(user) if user else {"phone": f"+{raw_phone}", "full_name": "Ahror Suyunov", "role": "resident", "account_id": db_manager.generate_unique_account_id("XP-")}
                    if not user_dict.get("account_id"):
                        user_dict["account_id"] = db_manager.generate_unique_account_id("XP-")
                    
                    status_2fa = db_manager.get_user_2fa_status(f"+{raw_phone}")
                    if not status_2fa.get("has_2fa"):
                        status_2fa = db_manager.get_user_2fa_status(raw_phone)

                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "ok": True,
                        "action": "login",
                        "user": user_dict,
                        "require_2fa": status_2fa.get("has_2fa", False),
                        "hint": status_2fa.get("hint", "")
                    }).encode("utf-8"))
                    return
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode("utf-8"))
            return

        # 1. AUTH REGISTER (Fuqaroni bazaga kiritish)
        if self.path == "/api/auth/register":
            try:
                length = int(self.headers.get("Content-Length", 0) or 0)
                body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
                data = json.loads(body)
                res = db_manager.register_user(
                    phone=data.get("phone", ""),
                    full_name=data.get("full_name", ""),
                    role=data.get("role", "resident"),
                    region=data.get("region", "qashqadaryo"),
                    district=data.get("district", "nishon"),
                    mfy=data.get("mfy", "koksoy"),
                    street=data.get("street", "koksoy_markaziy"),
                    house_number=data.get("house_number", "1-uy")
                )
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(res).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode("utf-8"))
            return

        # 2. AUTH LOGIN & VALIDATION
        # 2FA SETUP (Telegram uslubida kalit so'z o'rnatish)
        if self.path == "/api/auth/set-2fa":
            try:
                length = int(self.headers.get("Content-Length", 0) or 0)
                body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
                data = json.loads(body)
                phone = data.get("phone", "").strip()
                passw = data.get("password", "").strip()
                hint = data.get("hint", "").strip()
                res = db_manager.set_user_2fa(phone, passw, hint)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(res).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode("utf-8"))
            return

        # 2FA VERIFY (Kalit so'zni tekshirish)
        if self.path == "/api/auth/verify-2fa":
            try:
                length = int(self.headers.get("Content-Length", 0) or 0)
                body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
                data = json.loads(body)
                phone = data.get("phone", "").strip()
                passw = data.get("password", "").strip()
                is_valid = db_manager.verify_user_2fa(phone, passw)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": is_valid}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode("utf-8"))
            return

        if self.path == "/api/auth/login":
            try:
                length = int(self.headers.get("Content-Length", 0) or 0)
                body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
                data = json.loads(body)
                phone = data.get("phone", "").strip()
                role = data.get("role", "resident")
                password = data.get("password", "").strip()

                if role == "driver":
                    raw_p = re.sub(r'\D', '', phone)
                    plate_input = str(data.get("truck_plate", "")).replace(" ", "").upper().strip()
                    password = str(data.get("password", "")).strip()

                    conn = db_manager.get_connection()
                    c = conn.cursor()
                    c.execute("SELECT * FROM drivers WHERE phone LIKE ?", (f"%{raw_p[-9:]}%",))
                    drivers = c.fetchall()
                    conn.close()

                    if not drivers:
                        resp = {"ok": False, "message": "❌ Ushbu telefon raqamli haydovchi topilmadi! Administratorga murojaat qiling."}
                    else:
                        matched = None
                        if plate_input:
                            for d in drivers:
                                d_plate = str(d["truck_plate"] or "").replace(" ", "").upper()
                                if d_plate == plate_input or plate_input in d_plate or d_plate in plate_input:
                                    matched = d
                                    break
                            if not matched:
                                resp = {"ok": False, "message": "❌ Mashina davlat raqami mos kelmadi! Administrator kiritgan raqamni kiriting."}
                            elif matched["password"] != password:
                                resp = {"ok": False, "message": "❌ Parol noto‘g‘ri! Administrator bergan parolni kiriting."}
                            else:
                                status_2fa = db_manager.get_user_2fa_status(matched["phone"])
                                matched_dict = dict(matched)
                                if not matched_dict.get("account_id"):
                                    matched_dict["account_id"] = db_manager.generate_unique_account_id("XP-")
                                resp = {
                                    "ok": True,
                                    "user": matched_dict,
                                    "require_2fa": status_2fa.get("has_2fa", False),
                                    "hint": status_2fa.get("hint", "")
                                }
                        else:
                            # If no plate provided, check first driver password
                            d = drivers[0]
                            if d["password"] != password:
                                resp = {"ok": False, "message": "❌ Parol noto‘g‘ri! Administrator bergan parolni kiriting."}
                            else:
                                status_2fa = db_manager.get_user_2fa_status(d["phone"])
                                resp = {
                                    "ok": True,
                                    "user": dict(d),
                                    "require_2fa": status_2fa.get("has_2fa", False),
                                    "hint": status_2fa.get("hint", "")
                                }
                else:
                    user = db_manager.get_user_by_phone(phone)
                    if not user:
                        resp = {"ok": False, "exists": False, "message": "Bu telefon raqam tizimda ro‘yxatdan o‘tmagan!"}
                    else:
                        status_2fa = db_manager.get_user_2fa_status(phone)
                        resp = {
                            "ok": True,
                            "user": user,
                            "require_2fa": status_2fa.get("has_2fa", False),
                            "hint": status_2fa.get("hint", "")
                        }

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(resp).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode("utf-8"))
            return

        # 3. SESSIONS HEARTBEAT & SYNC
        if self.path == "/api/sessions/sync":
            try:
                length = int(self.headers.get("Content-Length", 0) or 0)
                body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
                data = json.loads(body)
                dev_id = data.get("device_id")
                phone = data.get("phone", "")
                dev_name = data.get("device_name", "Android")
                os_name = data.get("os_name", "Android")
                ip = data.get("ip", self.client_address[0])

                if dev_id and phone:
                    db_manager.update_or_create_session(dev_id, phone, dev_name, os_name, ip)

                is_active = db_manager.check_session_active(dev_id) if dev_id else True
                sessions = db_manager.get_user_sessions(phone) if phone else []

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "ok": True,
                    "is_active": is_active,
                    "sessions": sessions
                }).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode("utf-8"))
            return

        # 4. SESSIONS TERMINATE
        if self.path == "/api/sessions/terminate":
            try:
                length = int(self.headers.get("Content-Length", 0) or 0)
                body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
                data = json.loads(body)
                dev_id = data.get("device_id")
                if dev_id:
                    db_manager.terminate_session(dev_id)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode("utf-8"))
            return

        # 5. SESSIONS TERMINATE ALL OTHERS
        if self.path == "/api/sessions/terminate-others":
            try:
                length = int(self.headers.get("Content-Length", 0) or 0)
                body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
                data = json.loads(body)
                phone = data.get("phone")
                cur_dev_id = data.get("current_device_id")
                if phone and cur_dev_id:
                    db_manager.terminate_other_sessions(phone, cur_dev_id)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode("utf-8"))
            return

        # 6. DRIVER LIVE LOCATION UPDATE (GPS)
        if self.path == "/api/driver/location":
            try:
                length = int(self.headers.get("Content-Length", 0) or 0)
                body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
                data = json.loads(body)
                phone = data.get("phone", "+998901234567")
                lat = data.get("lat", 38.665)
                lng = data.get("lng", 65.698)
                stat = data.get("status")
                stg = data.get("stage")
                st_k = data.get("street")
                st_n = data.get("street_name")
                db_manager.update_driver_location(phone, lat, lng, stat, stg, st_k, st_n)

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode("utf-8"))
            return

        if self.path == "/api/send-alert":
            try:
                length = int(self.headers.get("Content-Length", 0) or 0)
                body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
                data = json.loads(body)
                st_k = data.get("street", "istiqlol")
                reg_k = data.get("region", "qashqadaryo")
                dist_k = data.get("district", "nishon")
                mfy_k = data.get("mfy", "yangi_nishon")
                stg = data.get("stage", "collect")
                drv_stat = data.get("status", "arrived")
                reg_n = data.get("region_name")
                dist_n = data.get("district_name")
                mfy_n = data.get("mfy_name")
                st_n = data.get("street_name")
                plate = data.get("plate") or data.get("truck_plate") or current_driver_state.get("truck_plate", "30 782 AGA")
                drv_n = data.get("driver_name") or current_driver_state.get("driver_name", "Islomov Javohir")
                drv_p = data.get("driver_phone") or current_driver_state.get("driver_phone", "+998 (90) 123-45-67")
                t_model = data.get("truck_model") or current_driver_state.get("truck_model", "Isuzu NPR 75")
                t_color = data.get("truck_color") or current_driver_state.get("truck_color", "Oq (Sariq chiziqli)")

                sent_count = broadcast_street_alert(
                    street_key=st_k,
                    reg_key=reg_k,
                    dist_key=dist_k,
                    mfy_key=mfy_k,
                    stage=stg,
                    status=drv_stat,
                    reg_name=reg_n,
                    dist_name=dist_n,
                    mfy_name=mfy_n,
                    street_name=st_n,
                    truck_model=t_model,
                    truck_plate=plate,
                    truck_color=t_color,
                    driver_name=drv_n,
                    driver_phone=drv_p
                )

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "*")
                self.end_headers()
                
                resp_msg = f"{sent_count} ta fuqaroga ({st_n or st_k}) Telegram xabarnoma yetkazildi." if sent_count > 0 else f"«{st_n or st_k}» bo‘yicha hozircha botda obunachi yo‘q."
                self.wfile.write(json.dumps({
                    "ok": True,
                    "sent_count": sent_count,
                    "target_address": current_driver_state["last_address_text"],
                    "street_name": st_n or st_k,
                    "message": resp_msg
                }).encode("utf-8"))
            except Exception as e:
                import traceback
                err_msg = traceback.format_exc()
                print("[API ERROR]:", err_msg)
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(e), "trace": err_msg}).encode("utf-8"))

        elif self.path == "/api/set-driver-status":
            try:
                length = int(self.headers.get("Content-Length", 0) or 0)
                body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
                data = json.loads(body)
                new_status = data.get("status", "arrived")
                current_driver_state["status"] = new_status
                if "street" in data:
                    current_driver_state["street"] = data["street"]
                if "region" in data:
                    current_driver_state["region"] = data["region"]
                if "district" in data:
                    current_driver_state["district"] = data["district"]
                if "mfy" in data:
                    current_driver_state["mfy"] = data["mfy"]
                if "stage" in data:
                    current_driver_state["stage"] = data["stage"]
                if "driver_name" in data:
                    current_driver_state["driver_name"] = data["driver_name"]
                if "driver_phone" in data:
                    current_driver_state["driver_phone"] = data["driver_phone"]
                if "plate" in data:
                    current_driver_state["truck_plate"] = data["plate"]
                if "truck_plate" in data:
                    current_driver_state["truck_plate"] = data["truck_plate"]
                if "truck_model" in data:
                    current_driver_state["truck_model"] = data["truck_model"]
                if "truck_color" in data:
                    current_driver_state["truck_color"] = data["truck_color"]
                if "last_address_text" in data:
                    current_driver_state["last_address_text"] = data["last_address_text"]
                elif "street_name" in data:
                    st_n = data.get("street_name")
                    rg_n = data.get("region_name", "")
                    ds_n = data.get("district_name", "")
                    mf_n = data.get("mfy_name", "")
                    current_driver_state["last_address_text"] = f"{rg_n}, {ds_n}, {mf_n}, {st_n}".strip(", ")
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "driver_state": current_driver_state}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
        elif self.path == "/api/sync-user":
            try:
                length = int(self.headers.get("Content-Length", 0) or 0)
                body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
                data = json.loads(body)
                phone_in = data.get("phone")
                digits, formatted = normalize_phone(phone_in)
                subs = load_subscribers()
                
                matched_user = None
                for cid, uinfo in subs.items():
                    if uinfo.get("raw_phone") == digits or (digits and digits in str(uinfo.get("phone", ""))):
                        matched_user = uinfo
                        break

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "ok": True,
                    "is_verified": matched_user is not None and matched_user.get("phone_verified", False),
                    "matched_user": matched_user
                }).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
        elif self.path == "/api/update-user-address":
            try:
                length = int(self.headers.get("Content-Length", 0) or 0)
                body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
                data = json.loads(body)
                phone_in = data.get("phone", "")
                digits, _ = normalize_phone(phone_in)
                addr_text = data.get("addressText", "")
                reg = data.get("region", "")
                dist = data.get("district", "")
                mfy = data.get("mfy", "")
                street = data.get("street", "")

                subs = load_subscribers()
                updated_count = 0
                for cid, user_data in subs.items():
                    u_raw = user_data.get("raw_phone", "")
                    u_phone = str(user_data.get("phone", ""))
                    if not digits or u_raw == digits or (digits and digits[-9:] in u_raw) or (digits and digits[-9:] in u_phone) or len(subs) == 1:
                        user_data["address"] = {
                            "region": reg,
                            "district": dist,
                            "mfy": mfy,
                            "street": street,
                            "street_label": addr_text
                        }
                        user_data["address_text"] = addr_text
                        updated_count += 1
                save_subscribers(subs)
                print(f"[API] Foydalanuvchi manzili sinxronlandi: {addr_text} ({updated_count} ta obunachi)")

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "updated": updated_count, "address": addr_text}).encode("utf-8"))
            except Exception as e:
                print(f"[API ERROR update-user-address]: {e}")
                self.send_response(500)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Jim rejimda ishlash
        return

def run_http_server():
    server = HTTPServer(("0.0.0.0", HTTP_PORT), AlertApiHandler)
    print(f"[BOT SERVER] HTTP Bridge running on http://localhost:{HTTP_PORT}")
    server.serve_forever()

# ========================================================
# 9. TELEGRAM LONG POLLING SIKLI
# ========================================================
def run_telegram_polling():
    print("[BOT] Xonadon+ Telegram Bot (@xonadon_plus_bot) ishga tushdi...")
    offset = None
    while True:
        try:
            url = f"{API_URL}/getUpdates?timeout=25"
            if offset is not None:
                url += f"&offset={offset}"

            req = urllib.request.Request(url, headers={"User-Agent": "XonadonPlusBot/1.0"})
            with urllib.request.urlopen(req, timeout=35) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            if data.get("ok"):
                for update in data.get("result", []):
                    offset = update["update_id"] + 1

                    if "message" in update:
                        handle_message(update["message"])
                    elif "callback_query" in update:
                        handle_callback(update["callback_query"])

        except Exception as e:
            time.sleep(2)

if __name__ == "__main__":
    # Yagona nusxa bo'lishini ta'minlash (Port 3005 lock)
    acquire_instance_lock()

    # HTTP serverini alohida thread da boshlaymiz
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()

    # Telegram bot polling ni asosiy oqimda yuritamiz
    run_telegram_polling()
