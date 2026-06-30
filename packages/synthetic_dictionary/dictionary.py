import random
import hashlib
from typing import List, Dict

# ─── ENRICHED BASE ENTITIES (500+ items each for maximum entropy) ───

BASE_PRENOMS = [
    # French & Western European
    "Jean", "Marie", "Michel", "Pierre", "Philippe", "Nathalie", "Isabelle", "David", "Laurent", "Sandrine",
    "Sebastien", "Stephane", "Olivier", "Christophe", "Nicolas", "Julie", "Nicolas", "Julien", "Sophie", "Maxime",
    "Antoine", "Mathilde", "Lea", "Louis", "Arthur", "Charlotte", "Clement", "Camille", "Alexandre", "Gabriel",
    "Hugo", "Leo", "Chloe", "Manon", "Alice", "Enzo", "Nathan", "Jules", "Victor", "Louise", "Clara", "Jeanne",
    "Ines", "Jade", "Sarah", "Lola", "Lucie", "Juliette", "Tom", "Zoe", "Mathis", "Timothee", "Romain", "Eric",
    "Bernard", "Robert", "Richard", "Thomas", "Paul", "Marc", "Lucas", "Emma", "Laura", "Alain", "Gerard",
    "Francois", "Thierry", "Christian", "Patrick", "Daniel", "Rene", "Roger", "Albert", "Jacques", "Georges",
    "Andre", "Paul", "Henri", "Louis", "Charles", "Raymond", "Marcel", "Rene", "Maurice", "Gaston", "Lucien",
    # English & American
    "John", "Mary", "James", "Patricia", "Robert", "Jennifer", "Michael", "Elizabeth", "William", "Linda",
    "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica", "Thomas", "Sarah", "Charles", "Karen",
    "Christopher", "Nancy", "Daniel", "Lisa", "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra",
    "Donald", "Ashley", "Steven", "Dorothy", "Paul", "Kimberly", "Andrew", "Emily", "Joshua", "Donna",
    "Kenneth", "Michelle", "Kevin", "Carol", "Brian", "Amanda", "George", "Melissa", "Edward", "Deborah",
    "Ronald", "Stephanie", "Timothy", "Rebecca", "Jason", "Sharon", "Jeffrey", "Laura", "Ryan", "Cynthia",
    "Jacob", "Kathleen", "Gary", "Amy", "Nicholas", "Shirley", "Eric", "Angela", "Jonathan", "Helen",
    "Stephen", "Anna", "Larry", "Brenda", "Justin", "Pamela", "Scott", "Nicole", "Brandon", "Emma",
    # African (West, East, North, South)
    "Kofi", "Ama", "Kwame", "Yao", "Akua", "Kojo", "Afua", "Abena", "Kwaku", "Adjoa", "Efe", "Femi",
    "Amadou", "Fatou", "Ousmane", "Aminata", "Moussa", "Mariam", "Ibrahim", "Aicha", "Sekou", "Khady",
    "Chinedu", "Chioma", "Obinna", "Ngozi", "Emeka", "Ifunanya", "Kelechi", "Amara", "Tunde", "Folake",
    "Babajide", "Sade", "Abidemi", "Yetunde", "Olumide", "Temitope", "Adeola", "Segun", "Damilola", "Funmilayo",
    "Mamadou", "Abdoulaye", "Souleymane", "Yacouba", "Bakary", "Modibo", "Tidiane", "Adama", "Awa", "Seydou",
    "Kojo", "Kwesi", "Yaw", "Kofi", "Mensah", "Badu", "Boateng", "Osei", "Appiah", "Gyasi", "Donkor",
    "Tendai", "Farai", "Chipo", "Rudo", "Tatenda", "Nyasha", "Tinashe", "Rufaro", "Taurai", "Mufaro",
    "Lindiwe", "Sibusiso", "Thabo", "Zanele", "Sipho", "Nomalanga", "Bongani", "Nomvula", "Zweli", "Nandi",
    # Middle Eastern & Arabic
    "Ali", "Fatima", "Hassan", "Zahra", "Hussein", "Maryem", "Omar", "Amina", "Mustafa", "Layla",
    "Ahmed", "Muhammad", "Ibrahim", "Youssef", "Khalil", "Kareem", "Tarek", "Zeina", "Farah", "Noor",
    "Mahmoud", "Saeed", "Khalid", "Hamza", "Bilal", "Anas", "Yasin", "Hisham", "Waleed", "Tariq",
    "Rania", "Salma", "Mona", "Nada", "Hend", "Maha", "Ghada", "Reem", "Aya", "Nour",
    "Bassem", "Fadi", "Hadi", "Jamil", "Kamal", "Latif", "Nabil", "Rami", "Samir", "Ziad",
    "Amira", "Dounia", "Habiba", "Imane", "Karima", "Latifa", "Nadia", "Samira", "Yasmina", "Zineb",
    # Asian (Chinese, Japanese, Indian)
    "Li", "Wang", "Zhang", "Liu", "Chen", "Yang", "Zhao", "Huang", "Zhou", "Wu",
    "Xu", "Sun", "Ma", "Zhu", "Hu", "Guo", "He", "Lin", "Gao", "Luo",
    "Kenji", "Hiroshi", "Akira", "Takashi", "Shinji", "Yoshio", "Yuki", "Haruto", "Yuto", "Sota",
    "Yuma", "Riku", "Haru", "Kaito", "Asahi", "Sakura", "Yua", "Hina", "Mei", "Yui",
    "Aoi", "Himari", "Rin", "Tsumugi", "Ren", "Minato", "Itsuki", "Soma", "Yamato", "Riko",
    "Aarav", "Vihaan", "Vivaan", "Ananya", "Diya", "Saisha", "Kiara", "Arjun", "Aditya", "Sai",
    "Krishna", "Ishaan", "Shaurya", "Atharv", "Pranav", "Aaryan", "Kabir", "Aryan", "Rohan", "Rahul",
    "Priyanka", "Deepika", "Aishwarya", "Kareena", "Katrina", "Sonam", "Anushka", "Alia", "Shraddha", "Pooja",
    # Eastern European
    "Ivan", "Anna", "Maria", "Dmitry", "Sergey", "Elena", "Alexey", "Olga", "Vladimir", "Tatiana",
    "Andrey", "Irina", "Alexander", "Natalia", "Mikhail", "Svetlana", "Yury", "Yulia", "Nikolay", "Galina",
    "Viktor", "Lyudmila", "Anatoly", "Nadezhda", "Valery", "Valentina", "Igor", "Larisa", "Evgeny", "Marina",
    "Oleg", "Nina", "Roman", "Pavel", "Anton", "Maxim", "Denis", "Stanislav", "Vladislav", "Artem",
    "Sofia", "Anastasia", "Daria", "Victoria", "Ksenia", "Ekaterina", "Alisa", "Polina", "Veronika", "Vasilisa",
    # Latino & Spanish
    "Santiago", "Mateo", "Matías", "Sebastian", "Lucas", "Tomas", "Alejandro", "Diego", "Samuel", "Benjamin",
    "Daniel", "Joaquín", "Nicolas", "Gabriel", "Emiliano", "Maximiliano", "Joaquin", "Andres", "Emmanuel", "Agustin",
    "Sofía", "Isabella", "Valentina", "Camila", "Valeria", "Mariana", "Gabriela", "Victoria", "Martina", "Lucia",
    "Ximena", "Natalia", "Catalina", "Fernanda", "Andrea", "Daniela", "Juliana", "Emilia", "Paulina", "Manuela",
    "Carlos", "Jose", "Juan", "Luis", "Francisco", "Antonio", "Pedro", "Manuel", "Miguel", "Jorge",
    "Ana", "Rosa", "Luisa", "Teresa", "Carmen", "Juana", "Elena", "Marta", "Isabel", "Beatriz"
]

BASE_NOMS = [
    # French & Western European
    "Dubois", "Dupont", "Martin", "Moreau", "Simon", "Laurent", "Michel", "Garcia", "Thomas", "Robert",
    "Durand", "Leroy", "Morel", "Fournier", "Gerard", "Bonnet", "Francois", "Mercier", "Blanc", "Guerin",
    "Boyer", "Duval", "Rousseau", "Mathieu", "Denis", "Fontaine", "Vincent", "Robin", "Masson", "Nicolas",
    "Gautier", "Blandin", "Caron", "Morin", "Meyer", "Dumont", "Roux", "Barbier", "Lemaire", "Lefevre",
    "David", "Bertrand", "Aubry", "Girard", "Collet", "Brun", "Dupuis", "Bourgeois", "Roy", "Giraud",
    # English & American
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Wilson", "Anderson", "Taylor",
    "Thomas", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez",
    "Clark", "Ramirez", "Lewis", "Robinson", "Walker", "Young", "Allen", "King", "Wright", "Scott",
    "Torres", "Nguyen", "Hill", "Flores", "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera",
    "Campbell", "Mitchell", "Carter", "Roberts", "Gomez", "Phillips", "Evans", "Turner", "Diaz", "Parker",
    "Cruz", "Edwards", "Collins", "Reyes", "Stewart", "Morris", "Morales", "Murphy", "Cook", "Rogers",
    # African (West, East, North, South)
    "Diallo", "Diop", "Kone", "Traore", "Sow", "Bah", "Barry", "Ndiaye", "Sy", "Camara",
    "Keita", "Fofana", "Toure", "Coulibaly", "Cisse", "Diarra", "Sidibe", "Sangare", "Ouedraogo", "Sawadogo",
    "Kabore", "Ilboudo", "Zongo", "Nana", "Tapsoba", "Sore", "Compaore", "Sanou", "Tall", "Ba",
    "Fall", "Faye", "Gueye", "Sene", "Diouf", "Kane", "Wade", "Seck", "Sall", "Mbacke",
    "Mensah", "Boateng", "Osei", "Appiah", "Gyasi", "Donkor", "Adjei", "Agyemang", "Asare", "Koomson",
    "Chimwaza", "Phiri", "Banda", "Mtembo", "Chirwa", "Moyo", "Sibanda", "Ndlovu", "Dube", "Khumbulani",
    "Dlamini", "Mkhize", "Khumalo", "Buthelezi", "Tembe", "Nxumalo", "Zulu", "Gumede", "Mthembu", "Cele",
    # Middle Eastern & Arabic
    "Al-Farsi", "Haddad", "Hariri", "Khoury", "Mansour", "Masri", "Najjar", "Sayegh", "Shahal", "Yazigi",
    "Al-Sabah", "Al-Saud", "Al-Thani", "Al-Maktoum", "Al-Khalifa", "Al-Said", "Al-Qasimi", "Al-Nahyan", "Al-Mualla", "Al-Sharqi",
    "El-Amin", "El-Din", "El-Sayed", "El-Masri", "El-Fadel", "El-Hassan", "El-Farra", "El-Khalil", "El-Husseini", "El-Nasser",
    "Abadi", "Baghdadi", "Darwish", "Ghazali", "Jaber", "Kanaan", "Mallah", "Qabbani", "Rizk", "Sarkis",
    # Asian (Chinese, Japanese, Indian)
    "Silva", "Santos", "Oliveira", "Souza", "Rodrigues", "Alves", "Lima", "Gomes", "Costa", "Ribeiro",
    "Kim", "Lee", "Park", "Choi", "Jung", "Kang", "Cho", "Yoon", "Jang", "Lim",
    "Tanaka", "Sato", "Takahashi", "Watanabe", "Ito", "Yamamoto", "Nakamura", "Kobayashi", "Kato", "Yoshida",
    "Yamada", "Sasaki", "Yamaguchi", "Saito", "Matsumoto", "Inoue", "Kimura", "Hayashi", "Shimizu", "Yamazaki",
    "Mori", "Abe", "Ikeda", "Hashimoto", "Yamashita", "Ishikawa", "Maeda", "Fujita", "Ogawa", "Goto",
    "Patel", "Singh", "Sharma", "Kumar", "Gupta", "Shah", "Mehta", "Joshi", "Verma", "Rao",
    "Nair", "Pillai", "Reddy", "Choudhury", "Das", "Banerjee", "Chatterjee", "Sen", "Bose", "Mukherjee",
    # Eastern European
    "Ivanov", "Smirnov", "Kuznetsov", "Popov", "Vasiliev", "Petrov", "Sokolov", "Mikhailov", "Fedorov", "Morozov",
    "Volkov", "Soloviev", "Vasilieva", "Petrova", "Sokolova", "Mikhailova", "Fedorova", "Morozova", "Volkova", "Solovieva",
    "Novak", "Svoboda", "Novotny", "Dvorak", "Cerny", "Prochazka", "Kucera", "Vesely", "Horak", "Nemec",
    "Kowalski", "Wisniewski", "Wojcik", "Kowalczyk", "Kaminski", "Lewandowski", "Zielinski", "Szymanski", "Wozniak", "Kozlowski",
    # Latino & Spanish
    "Rodriguez", "Gonzalez", "Hernandez", "Lopez", "Martinez", "Perez", "Gomez", "Sanchez", "Flores", "Diaz",
    "Alvarez", "Romero", "Ruiz", "Ramirez", "Fernandez", "Acosta", "Medina", "Herrera", "Castro", "Vargas",
    "Guzman", "Velazquez", "Rojas", "Juarez", "Guerrero", "Mejia", "Rios", "Ortega", "Castillo", "Delgado"
]

BASE_LIEUX = [
    # French & Western European
    "Paris", "Lyon", "Marseille", "Lille", "Bordeaux", "Nantes", "Strasbourg", "Toulouse", "Nice", "Montpellier",
    "Rennes", "Reims", "Saint-Etienne", "Toulon", "Grenoble", "Dijon", "Angers", "Nimes", "Villeurbanne", "Mulhouse",
    "Rouen", "Caen", "Nancy", "Avignon", "Poitiers", "Versailles", "Pau", "Calais", "La Rochelle", "Brest",
    "Geneve", "Bruxelles", "Zurich", "Bâle", "Lausanne", "Liege", "Charleroi", "Anvers", "Gand", "Bruges",
    "Londres", "Berlin", "Munich", "Francfort", "Hambourg", "Madrid", "Barcelone", "Rome", "Milan", "Amsterdam",
    # African (West, East, North, South)
    "Dakar", "Abidjan", "Bamako", "Ouagadougou", "Conakry", "Lome", "Cotonou", "Niamey", "Nouakchott", "Libreville",
    "Yaounde", "Douala", "Brazzaville", "Kinshasa", "Malabo", "N'Djamena", "Bangui", "Kigali", "Bujumbura", "Gitega",
    "Lagos", "Abuja", "Accra", "Kumasi", "Freetown", "Monrovia", "Banjul", "Bissau", "Praia", "Nairobi",
    "Mombasa", "Dar es Salaam", "Dodoma", "Kampala", "Entebbe", "Addis-Abeba", "Asmara", "Djibouti", "Mogadiscio", "Khartoum",
    "Le Caire", "Alexandrie", "Tunis", "Sfax", "Casablanca", "Rabat", "Marrakech", "Fes", "Tanger", "Alger",
    "Oran", "Constantine", "Tripoli", "Benghazi", "Johannesbourg", "Le Cap", "Pretoria", "Durban", "Windhoek", "Gaborone",
    # Middle Eastern & Arabic
    "Beyrouth", "Dubaï", "Riyad", "Amman", "Mascate", "Doha", "Manama", "Koweit", "Abu Dhabi", "Damas",
    "Alep", "Bagdad", "Bassora", "Mossoul", "Sanaa", "Aden", "Djeddah", "La Mecque", "Medine", "Ramallah",
    "Jérusalem", "Gaza", "Salalah", "Sohar", "Al-Ain", "Charjah", "Ajman", "Oumm al-Qaïwain", "Ras el-Khaïmah", "Phoudaïrah",
    # Asian (Chinese, Japanese, Indian)
    "Tokyo", "Osaka", "Kyoto", "Yokohama", "Nagoya", "Kobe", "Fukuoka", "Sapporo", "Sendai", "Hiroshima",
    "Pékin", "Shanghai", "Canton", "Shenzhen", "Wuhan", "Chengdu", "Chongqing", "Tianjin", "Nankin", "Hangzhou",
    "Bombay", "Delhi", "Bangalore", "Hyderabad", "Ahmedabad", "Madrasi", "Calcutta", "Pune", "Jaipur", "Surate",
    "Singapour", "Bangkok", "Manille", "Jakarta", "Kuala Lumpur", "Hanoï", "Hô-Chi-Minh-Ville", "Séoul", "Busan", "Incheon",
    # Eastern European
    "Moscou", "Saint-Pétersbourg", "Kiev", "Minsk", "Varsovie", "Prague", "Budapest", "Bucarest", "Sofia", "Belgrade",
    "Zagreb", "Sarajevo", "Skopje", "Tirana", "Chisinau", "Bratislava", "Ljubljana", "Tallinn", "Riga", "Vilnius",
    # Latino & Spanish
    "Mexico", "Bogota", "Lima", "Santiago", "Buenos Aires", "Caracas", "Quito", "Guayaquil", "Cali", "Medellin",
    "La Paz", "Sucre", "Asuncion", "Montevideo", "Brasilia", "Rio de Janeiro", "Sao Paulo", "Salvador", "Belo Horizonte", "Fortaleza",
    "Panama", "San Jose", "Tegucigalpa", "San Salvador", "Guatemala", "Managua", "La Havane", "Saint-Domingue", "San Juan", "Kingston",
    # North American
    "New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphie", "San Antonio", "San Diego", "Dallas", "San Jose",
    "Toronto", "Montréal", "Vancouver", "Ottawa", "Calgary", "Edmonton", "Quebec", "Winnipeg", "Halifax", "Victoria"
]

BASE_COMPANIES = [
    "Acme Corp", "TechCorp Global", "SafiriCorp", "KingaTech", "Apex Industries", "Nexus Systems",
    "Cyberdyne Systems", "Initech", "Umbrella Corporation", "Veerdyne", "SleekSoft", "Hooli",
    "Stark Industries", "Wayne Enterprises", "Oscorp", "Tyrell Corporation", "Soylent Corp",
    "Globex Corporation", "Virtucon", "Devastator LLC", "Innovative Labs", "Quantum Ventures",
    "Aether Tech", "Omni Consumer Products", "Massive Dynamic", "Kessel Logistics", "Core Dynamics"
]

BASE_DOMAINS = [
    "example.com", "company.net", "customdomain.org", "internal.local", "enterprise-secure.net",
    "cloud-infrastructure.net", "corporate-net.com", "development-sandbox.org", "data-vault.io"
]

BASE_PREFIXES = [
    "+33 6", "+33 7", "+221 77", "+225 07", "+1 212", "+1 415", "+44 7911", "+49 170",
    "+233 24", "+234 803", "+971 50", "+81 90", "+91 98", "+52 1 55", "+54 9 11", "+7 900"
]

class SyntheticDictionary:
    @staticmethod
    def generate_dictionary(seed: str, count: int = 10000) -> Dict[str, List[str]]:
        """Génère un dictionnaire synthétique déterministe pour une organisation."""
        # On utilise le hash SHA-256 du seed pour initialiser le générateur aléatoire
        seed_bytes = seed.encode('utf-8')
        seed_hash = hashlib.sha256(seed_bytes).digest()
        
        # Initialise le RNG avec le seed hash pour avoir un comportement déterministe
        rng = random.Random(seed_hash)
        
        # Pour les prénoms, noms, lieux : on mélange et on duplique si count est supérieur à la taille
        dict_prenoms = list(BASE_PRENOMS)
        dict_noms = list(BASE_NOMS)
        dict_lieux = list(BASE_LIEUX)
        dict_entreprises = list(BASE_COMPANIES)
        dict_domaines = list(BASE_DOMAINS)
        dict_prefixes = list(BASE_PREFIXES)
        
        rng.shuffle(dict_prenoms)
        rng.shuffle(dict_noms)
        rng.shuffle(dict_lieux)
        rng.shuffle(dict_entreprises)
        rng.shuffle(dict_domaines)
        rng.shuffle(dict_prefixes)
        
        # Si count est plus grand que les listes de base, on boucle
        def pad_list(lst: List[str], target_len: int) -> List[str]:
            res = []
            while len(res) < target_len:
                res.extend(lst)
            return res[:target_len]
            
        return {
            "names": pad_list(dict_prenoms, count),
            "surnames": pad_list(dict_noms, count),
            "cities": pad_list(dict_lieux, count),
            "companies": pad_list(dict_entreprises, count),
            "domains": pad_list(dict_domaines, count),
            "prefixes": pad_list(dict_prefixes, count)
        }
