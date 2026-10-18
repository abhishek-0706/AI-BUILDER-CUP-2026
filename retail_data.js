// Synthetic Protiva demo data. Published sources retain their provenance.
// JSON-compatible object shared by the browser, seed generator and API.
const RETAIL_DATA = {
  "brand": {
    "name": "Protiva",
    "positioning": "Everyday protein nutrition for Indian households, sold through modern trade."
  },
  "store": {
    "name": "FreshMart Express, Koramangala",
    "city": "Bengaluru",
    "zone": "South India",
    "storeId": "BLR-KOR-014",
    "sqft": 4200,
    "segment": "Urban Grocery",
    "openDate": "2021-03-15"
  },
  "categories": [
    "Protein Bars",
    "Ready-to-Drink Protein Shakes",
    "Chilled Salads"
  ],
  "products": [
    {
      "id": "B01",
      "name": "Protiva Oats and Nut Bar",
      "cat": "Protein Bars",
      "pack": "40g",
      "price": 45,
      "stock": 110,
      "reorderAt": 50,
      "unitsSoldLast30d": 960,
      "margin": 0.26,
      "protein": 8,
      "addedSugar": 4,
      "trending": false,
      "ours": true
    },
    {
      "id": "B02",
      "name": "Protiva Protein Bar Peanut Jaggery",
      "cat": "Protein Bars",
      "pack": "45g",
      "price": 55,
      "stock": 84,
      "reorderAt": 40,
      "unitsSoldLast30d": 740,
      "margin": 0.24,
      "protein": 10,
      "addedSugar": 5,
      "trending": false,
      "ours": true
    },
    {
      "id": "B03",
      "name": "Protiva Protein Bar Choco Almond",
      "cat": "Protein Bars",
      "pack": "45g",
      "price": 60,
      "stock": 96,
      "reorderAt": 40,
      "unitsSoldLast30d": 820,
      "margin": 0.24,
      "protein": 12,
      "addedSugar": 5,
      "trending": true,
      "ours": true
    },
    {
      "id": "B04",
      "name": "Protiva Protein Bar Coffee Cocoa",
      "cat": "Protein Bars",
      "pack": "45g",
      "price": 65,
      "stock": 52,
      "reorderAt": 30,
      "unitsSoldLast30d": 410,
      "margin": 0.23,
      "protein": 12,
      "addedSugar": 4,
      "trending": true,
      "ours": true
    },
    {
      "id": "R01",
      "name": "Protiva Protein Shake Chocolate",
      "cat": "Ready-to-Drink Protein Shakes",
      "pack": "200ml",
      "price": 70,
      "stock": 64,
      "reorderAt": 36,
      "unitsSoldLast30d": 520,
      "margin": 0.22,
      "protein": 20,
      "addedSugar": 3,
      "trending": true,
      "ours": true
    },
    {
      "id": "R02",
      "name": "Protiva Protein Shake Coffee",
      "cat": "Ready-to-Drink Protein Shakes",
      "pack": "200ml",
      "price": 75,
      "stock": 48,
      "reorderAt": 30,
      "unitsSoldLast30d": 430,
      "margin": 0.22,
      "protein": 20,
      "addedSugar": 3,
      "trending": true,
      "ours": true
    },
    {
      "id": "R03",
      "name": "Protiva Protein Shake Vanilla",
      "cat": "Ready-to-Drink Protein Shakes",
      "pack": "200ml",
      "price": 70,
      "stock": 28,
      "reorderAt": 30,
      "unitsSoldLast30d": 310,
      "margin": 0.21,
      "protein": 20,
      "addedSugar": 4,
      "trending": false,
      "ours": true
    },
    {
      "id": "R04",
      "name": "Protiva High Protein Shake 30g",
      "cat": "Ready-to-Drink Protein Shakes",
      "pack": "330ml",
      "price": 125,
      "stock": 26,
      "reorderAt": 18,
      "unitsSoldLast30d": 180,
      "margin": 0.2,
      "protein": 30,
      "addedSugar": 2,
      "trending": false,
      "ours": true
    },
    {
      "id": "S01",
      "name": "Protiva Chickpea and Quinoa Salad Bowl",
      "cat": "Chilled Salads",
      "pack": "200g",
      "price": 149,
      "stock": 7,
      "reorderAt": 8,
      "unitsSoldLast30d": 88,
      "margin": 0.3,
      "protein": 18,
      "addedSugar": 0,
      "trending": false,
      "ours": true,
      "shelfLifeDays": 4
    },
    {
      "id": "S02",
      "name": "Protiva Paneer Tikka Protein Salad",
      "cat": "Chilled Salads",
      "pack": "200g",
      "price": 179,
      "stock": 14,
      "reorderAt": 10,
      "unitsSoldLast30d": 124,
      "margin": 0.28,
      "protein": 22,
      "addedSugar": 0,
      "trending": true,
      "ours": true,
      "shelfLifeDays": 4
    },
    {
      "id": "S03",
      "name": "Protiva Chicken Caesar Protein Salad",
      "cat": "Chilled Salads",
      "pack": "220g",
      "price": 199,
      "stock": 11,
      "reorderAt": 8,
      "unitsSoldLast30d": 96,
      "margin": 0.28,
      "protein": 26,
      "addedSugar": 0,
      "trending": true,
      "ours": true,
      "shelfLifeDays": 4
    },
    {
      "id": "C01",
      "name": "Hershey's Milkshake 200ml",
      "cat": "Ready-to-Drink Protein Shakes",
      "pack": "200ml",
      "price": 45,
      "stock": 186,
      "reorderAt": 60,
      "unitsSoldLast30d": 960,
      "margin": 0.19,
      "protein": 5,
      "addedSugar": 21,
      "trending": false,
      "ours": false
    },
    {
      "id": "C02",
      "name": "Sofit Soya 200ml",
      "cat": "Ready-to-Drink Protein Shakes",
      "pack": "200ml",
      "price": 55,
      "stock": 118,
      "reorderAt": 40,
      "unitsSoldLast30d": 540,
      "margin": 0.2,
      "protein": 7,
      "addedSugar": 12,
      "trending": false,
      "ours": false
    }
  ],
  "revenueWeek": [
    {
      "day": "Monday",
      "revenue": 212160,
      "transactions": 312
    },
    {
      "day": "Tuesday",
      "revenue": 184870,
      "transactions": 278
    },
    {
      "day": "Wednesday",
      "revenue": 240810,
      "transactions": 349
    },
    {
      "day": "Thursday",
      "revenue": 195552,
      "transactions": 291
    },
    {
      "day": "Friday",
      "revenue": 315135,
      "transactions": 447
    },
    {
      "day": "Saturday",
      "revenue": 429364,
      "transactions": 598
    },
    {
      "day": "Sunday",
      "revenue": 446424,
      "transactions": 627
    }
  ],
  "forecast": [
    {
      "day": "Monday",
      "predicted": 208000,
      "lower": 186000,
      "upper": 230000
    },
    {
      "day": "Tuesday",
      "predicted": 195000,
      "lower": 174000,
      "upper": 216000
    },
    {
      "day": "Wednesday",
      "predicted": 249000,
      "lower": 224000,
      "upper": 274000
    },
    {
      "day": "Thursday",
      "predicted": 218000,
      "lower": 195000,
      "upper": 241000
    },
    {
      "day": "Friday",
      "predicted": 322000,
      "lower": 290000,
      "upper": 354000
    },
    {
      "day": "Saturday",
      "predicted": 431000,
      "lower": 389000,
      "upper": 473000
    },
    {
      "day": "Sunday",
      "predicted": 444000,
      "lower": 401000,
      "upper": 487000
    }
  ],
  "segments": [
    {
      "name": "Weekend Stock-Up",
      "pct": 34,
      "avgBasket": 1150,
      "visits": 1.4,
      "desc": "Bulk weekend trips, high-value baskets"
    },
    {
      "name": "Daily Top-Ups",
      "pct": 28,
      "avgBasket": 330,
      "visits": 5.8,
      "desc": "Small daily purchases, highly loyal"
    },
    {
      "name": "Deal Seekers",
      "pct": 22,
      "avgBasket": 620,
      "visits": 2.1,
      "desc": "Price-sensitive, respond to promotions"
    },
    {
      "name": "Grab and Go",
      "pct": 16,
      "avgBasket": 575,
      "visits": 2.9,
      "desc": "Single-serve immediate consumption"
    }
  ],
  "alerts": [
    {
      "product": "Protiva Chickpea and Quinoa Salad Bowl",
      "level": "critical",
      "stock": 7,
      "reorderAt": 8,
      "trigger": "Below reorder point",
      "action": "Daily drop required, 4-day shelf life"
    },
    {
      "product": "Protiva Protein Shake Vanilla",
      "level": "critical",
      "stock": 28,
      "reorderAt": 30,
      "trigger": "Below reorder point",
      "action": "Reorder 240 units today"
    },
    {
      "product": "Protiva Chicken Caesar Protein Salad",
      "level": "warning",
      "stock": 11,
      "reorderAt": 8,
      "trigger": "Shrink risk on 4-day life",
      "action": "Two days of cover, watch shrink"
    },
    {
      "product": "Protiva High Protein Shake 30g",
      "level": "warning",
      "stock": 26,
      "reorderAt": 18,
      "trigger": "Must-win target gap",
      "action": "180 of 400 units achieved"
    }
  ],
  "promotions": [
    {
      "name": "Protein Pledge Bundle",
      "discount": "Buy 1 bar with 1 shake, save ₹20",
      "validity": "3 November to 30 November",
      "uplift": "+23% units, +41% basket value",
      "skuIds": [
        "B01",
        "B02",
        "B03",
        "B04",
        "R01",
        "R02"
      ],
      "startDate": "2026-11-03",
      "endDate": "2026-11-30"
    },
    {
      "name": "Choco Almond Offer",
      "discount": "10% off Choco Almond bar",
      "validity": "All month",
      "uplift": "+9% units",
      "skuIds": [
        "B03"
      ],
      "startDate": "2026-10-01",
      "endDate": "2026-10-31"
    },
    {
      "name": "Salad Fresh Hour",
      "discount": "₹20 off chilled salads before 6pm",
      "validity": "Daily",
      "uplift": "shrink 6.1% down to 2.4%",
      "skuIds": [
        "S01",
        "S02",
        "S03"
      ],
      "startDate": "2026-10-01",
      "endDate": "2026-10-31"
    }
  ],
  "shopperProfiles": [
    {
      "id": "S1",
      "name": "Priya",
      "age": 32,
      "role": "Software Engineer",
      "preferences": [
        "high protein",
        "low added sugar",
        "quick breakfast"
      ],
      "recentBuys": [
        "Protiva Protein Shake Chocolate",
        "Protiva Protein Bar Choco Almond"
      ],
      "basket": [
        "Protiva Protein Shake Chocolate"
      ]
    },
    {
      "id": "S2",
      "name": "Rahul",
      "age": 45,
      "role": "Gym Owner",
      "preferences": [
        "bulk",
        "most protein per rupee",
        "value packs"
      ],
      "recentBuys": [
        "Protiva High Protein Shake 30g",
        "Protiva Oats and Nut Bar"
      ],
      "basket": []
    },
    {
      "id": "S3",
      "name": "Guest Shopper",
      "age": null,
      "role": null,
      "preferences": [],
      "recentBuys": [],
      "basket": []
    }
  ],
  "rep": {
    "name": "Anita Sharma",
    "role": "Territory Sales Executive",
    "territory": "Bengaluru South",
    "employeeId": "TSE-4417",
    "quotaMonth": 2400000,
    "achievedMonth": 1812000,
    "visitsPlanned": 22,
    "visitsDone": 14,
    "monthDaysTotal": 31,
    "monthDaysElapsed": 22
  },
  "targets": {
    "period": "October 2026",
    "byAccount": [
      {
        "account": "FreshMart Express",
        "target": 1400000,
        "achieved": 1095000
      },
      {
        "account": "DailyNeeds Supermart",
        "target": 700000,
        "achieved": 462000
      },
      {
        "account": "General Trade (other outlets)",
        "target": 300000,
        "achieved": 255000
      }
    ],
    "byCategory": [
      {
        "cat": "Protein Bars",
        "target": 900000,
        "achieved": 760000,
        "focus": true
      },
      {
        "cat": "Ready-to-Drink Protein Shakes",
        "target": 820000,
        "achieved": 520000,
        "focus": true
      },
      {
        "cat": "Chilled Salads",
        "target": 430000,
        "achieved": 352000,
        "focus": false
      },
      {
        "cat": "Trade Promotions",
        "target": 250000,
        "achieved": 180000,
        "focus": false
      }
    ],
    "mustWinSKUs": [
      {
        "name": "Protiva Protein Shake Chocolate",
        "target": 650,
        "achieved": 520
      },
      {
        "name": "Protiva High Protein Shake 30g",
        "target": 400,
        "achieved": 180
      },
      {
        "name": "Protiva Paneer Tikka Protein Salad",
        "target": 140,
        "achieved": 124
      }
    ]
  },
  "accounts": [
    {
      "id": "ACC-01",
      "name": "FreshMart Express",
      "type": "Modern Trade, Urban Grocery",
      "stores": 14,
      "tier": "Platinum",
      "relationship": "7 years",
      "ytdValue": 18400000,
      "growthYoY": 0.12,
      "contact": {
        "name": "Vikram Rao",
        "role": "Category Buyer, Chilled and Packaged Foods",
        "style": "Arrives with his own numbers, trades facings only against proven throughput per facing, and ends the meeting at the stated time whether or not you are finished"
      }
    },
    {
      "id": "ACC-02",
      "name": "DailyNeeds Supermart",
      "type": "Modern Trade, Value Format",
      "stores": 31,
      "tier": "Gold",
      "relationship": "3 years",
      "ytdValue": 9200000,
      "growthYoY": -0.04,
      "contact": {
        "name": "Meera Iyer",
        "role": "Regional Merchandising Head",
        "style": "Opens on price and promo funding, benchmarks every ask against her private label, and will not discuss range before she has a fill-rate answer"
      }
    }
  ],
  "visits": [
    {
      "id": "V-00118",
      "accountId": "ACC-01",
      "store": "FreshMart Express, Koramangala",
      "storeId": "BLR-KOR-014",
      "date": "2026-10-22",
      "time": "10:30",
      "duration": "90 minutes",
      "status": "scheduled",
      "lastVisit": "2026-09-11",
      "daysSince": 41,
      "visitFrequency": "every 5-7 days (Index Score based)",
      "objective": "Get the fourth-quarter reset executed in the chilled bay. Protiva is listed for 13 facings and currently has none on shelf.",
      "openTasks": [
        "Audit the chilled protein bay against the fourth-quarter planogram reset",
        "Establish the first Protiva facings in the chilled bay",
        "Resolve 18 salad write-offs raised last visit",
        "Present the cost per gram of protein case against Hershey's and Sofit"
      ],
      "history": {
        "lastOrderValue": 58000,
        "ordersLast6m": 29,
        "avgOrderValue": 52000,
        "listingsLost": [
          "Chilled bay reset agreed for the fourth quarter but never executed, Protiva at 0 of 13 assigned facings"
        ],
        "pastObjections": [
          "Your 330ml shake sits at ₹125 next to a Hershey's milkshake at ₹45, and it moved 180 units last month against 960 for the Hershey's vanilla. Tell me why it earns a facing at all.",
          "You want 13 of the 44 facings in that bay, so 30 percent, for a brand that has never held a facing in it. Name the product I pull to pay for it.",
          "Your Chicken Caesar is ₹199 on a four-day life and I wrote off 18 salad packs last month. A 28 percent margin does not survive that shrink, so your real margin is closer to 22."
        ]
      }
    },
    {
      "id": "V-00119",
      "accountId": "ACC-02",
      "store": "DailyNeeds Supermart, Jayanagar",
      "storeId": "BLR-JAY-007",
      "date": "2026-10-23",
      "time": "14:00",
      "duration": "60 minutes",
      "status": "scheduled",
      "lastVisit": "2026-10-09",
      "daysSince": 13,
      "visitFrequency": "every 14 days",
      "objective": "Arrest the 4 percent year on year decline and open the ready-to-drink shake range before the Protein Pledge burst",
      "openTasks": [
        "Close the August fill-rate complaint with the September scorecard",
        "Re-negotiate shelf share in the bar bay"
      ],
      "history": {
        "lastOrderValue": 31000,
        "ordersLast6m": 16,
        "avgOrderValue": 29000,
        "listingsLost": [],
        "pastObjections": [
          "₹60 for one 45g bar in a value format. My best-selling bar is ₹30 and my own label is ₹25. Where is your ₹35 pack or your six-pack under ₹300?",
          "Your chilled fill rate was 86 percent in August and I had empty hooks for eleven days on a line I was promoting. I am not adding four shake products until I see three clean months.",
          "I funded 15 percent off your Choco Almond bar and got 9 percent more units. That cost me money per unit. Why would I run the same promotion again this quarter?"
        ]
      }
    }
  ],
  "visitPlan": [
    {
      "store": "FreshMart Express, Koramangala",
      "storeId": "BLR-KOR-014",
      "account": "FreshMart Express",
      "daysSince": 41,
      "cadenceDays": 6,
      "openTasks": 4,
      "revenueAtRisk": 142000,
      "targetGap": 305000,
      "scheduled": "2026-10-22 10:30"
    },
    {
      "store": "DailyNeeds Supermart, Jayanagar",
      "storeId": "BLR-JAY-007",
      "account": "DailyNeeds Supermart",
      "daysSince": 13,
      "cadenceDays": 14,
      "openTasks": 2,
      "revenueAtRisk": 86000,
      "targetGap": 238000,
      "scheduled": "2026-10-23 14:00"
    },
    {
      "store": "FreshMart Express, HSR Layout",
      "storeId": "BLR-HSR-021",
      "account": "FreshMart Express",
      "daysSince": 9,
      "cadenceDays": 6,
      "openTasks": 1,
      "revenueAtRisk": 118000,
      "targetGap": 305000,
      "scheduled": null
    },
    {
      "store": "DailyNeeds Supermart, BTM",
      "storeId": "BLR-BTM-033",
      "account": "DailyNeeds Supermart",
      "daysSince": 22,
      "cadenceDays": 14,
      "openTasks": 3,
      "revenueAtRisk": 74000,
      "targetGap": 238000,
      "scheduled": null
    },
    {
      "store": "FreshMart Express, Indiranagar",
      "storeId": "BLR-IND-008",
      "account": "FreshMart Express",
      "daysSince": 4,
      "cadenceDays": 6,
      "openTasks": 0,
      "revenueAtRisk": 96000,
      "targetGap": 305000,
      "scheduled": null
    },
    {
      "store": "DailyNeeds Supermart, Banashankari",
      "storeId": "BLR-BAN-019",
      "account": "DailyNeeds Supermart",
      "daysSince": 31,
      "cadenceDays": 14,
      "openTasks": 2,
      "revenueAtRisk": 58000,
      "targetGap": 238000,
      "scheduled": null
    }
  ],
  "marketing": [
    {
      "title": "Protein Pledge burst goes live 3 November",
      "type": "Campaign",
      "detail": "A four-week digital and in-store burst across Bengaluru, Hyderabad and Chennai, built around the bar plus shake bundle rather than a price cut. Chiller cling and shelf-edge strips ship to stores from 27 October.",
      "relevance": "The bundle mechanic answers Meera's discount objection directly, and it is the reason to get chilled facings executed before 3 November, not after."
    },
    {
      "title": "Ready-to-drink protein is the fastest-growing chilled drinks format",
      "type": "Category signal",
      "detail": "The format grew 31.2 percent year on year in Indian modern trade while total packaged dairy beverages grew 4.8 percent. Single-serve 200ml accounts for 68 percent of occasions.",
      "relevance": "Gives Vikram a category reason to reallocate facings rather than a brand reason, which is the only argument that moves him."
    },
    {
      "title": "Hershey's and Sofit hold 23 of the 44 facings in this bay",
      "type": "Competitive alert",
      "detail": "Hershey's added two 200ml milkshake flavours in September and holds 14 facings. Sofit holds 9 after putting a high-protein soya claim on pack at ₹55. Neither carries more than 7g protein per 200ml.",
      "relevance": "Protiva holds none of the 44 against 13 assigned by the fourth-quarter reset, so the facings ask has to be made at this visit, using the cost per gram of protein line in KB-108."
    },
    {
      "title": "In-store searches for 'high protein' up 41 percent in 30 days",
      "type": "Consumer signal",
      "detail": "Measured across the shopper assistant's query logs in Bengaluru South. Searches for 'protein shake' outgrew 'milkshake' for the first time in September.",
      "relevance": "Evidence that demand is pulling the format, which supports taking eye level rather than accepting a bottom shelf compromise."
    }
  ],
  "team": [
    {
      "name": "Anita Sharma",
      "territory": "Bengaluru South",
      "quota": 2400000,
      "achieved": 1812000,
      "visitsPlanned": 22,
      "visitsDone": 14,
      "outletsCovered": 18,
      "outletsTotal": 24,
      "avgPitchScore": 71,
      "rehearsalsDone": 9,
      "complianceRate": 0.82,
      "strikeRate": 0.58
    },
    {
      "name": "Rohit Menon",
      "territory": "Bengaluru East",
      "quota": 2200000,
      "achieved": 2046000,
      "visitsPlanned": 20,
      "visitsDone": 19,
      "outletsCovered": 21,
      "outletsTotal": 22,
      "avgPitchScore": 84,
      "rehearsalsDone": 16,
      "complianceRate": 0.91,
      "strikeRate": 0.72
    },
    {
      "name": "Kavya Reddy",
      "territory": "Bengaluru North",
      "quota": 2000000,
      "achieved": 1180000,
      "visitsPlanned": 20,
      "visitsDone": 11,
      "outletsCovered": 12,
      "outletsTotal": 23,
      "avgPitchScore": 54,
      "rehearsalsDone": 2,
      "complianceRate": 0.64,
      "strikeRate": 0.39
    },
    {
      "name": "Imran Qureshi",
      "territory": "Bengaluru West",
      "quota": 2100000,
      "achieved": 1743000,
      "visitsPlanned": 21,
      "visitsDone": 16,
      "outletsCovered": 17,
      "outletsTotal": 21,
      "avgPitchScore": 68,
      "rehearsalsDone": 7,
      "complianceRate": 0.79,
      "strikeRate": 0.55
    }
  ],
  "kbDocs": [
    {
      "id": "KB-101",
      "title": "[SYNTHETIC] Nielsen Retail Audit, India Protein and Active Nutrition, Q3 2026",
      "fact": "Ready-to-drink protein grew 31.2% year on year in Indian modern trade against 4.8% for total packaged dairy beverages."
    },
    {
      "id": "KB-102",
      "title": "[SYNTHETIC] FreshMart Koramangala Category Performance Report, September 2026",
      "fact": "Protein and active nutrition delivered 2.8% of store revenue from 1.1% of store shelf space, the highest revenue per running foot of any chilled sub-category."
    },
    {
      "id": "KB-103",
      "title": "[SYNTHETIC] Internal Margin Sheet, October to December 2026 Trade Terms",
      "fact": "Protiva ready-to-drink shakes carry a 20 to 22% retailer margin against a 19% chilled dairy drinks bay average, with a 3% fourth-quarter volume rebate above 1,200 units per store per quarter."
    },
    {
      "id": "KB-104",
      "title": "[SYNTHETIC] Shopper Panel Study, Bengaluru Urban Protein Buyers, August 2026",
      "fact": "68% of ready-to-drink protein purchases in Bengaluru modern trade are single-bottle immediate-consumption trips, and 54% of those shoppers also pick up a bar in the same basket."
    },
    {
      "id": "KB-105",
      "title": "[SYNTHETIC] Planogram Placement Test, 9 Bengaluru Modern Trade Stores, July 2026",
      "fact": "Moving a 330ml high-protein product from shelf 4 to shelf 2 at eye level lifted its units per store per week from 11 to 26, a 136% increase, with no decline in the 200ml packs beside it."
    },
    {
      "id": "KB-106",
      "title": "[SYNTHETIC] Protein Pledge Promotion Post-Mortem, June 2026",
      "fact": "A 15% price cut on Protiva Choco Almond bars delivered 9% unit uplift, while a buy-one-bar-with-one-shake bundle at full price delivered 23% uplift and a 41% higher basket value."
    },
    {
      "id": "KB-107",
      "title": "[SYNTHETIC] Supply Chain Scorecard, September 2026",
      "fact": "Chilled fill rate on Protiva ready-to-drink shakes recovered to 97.1% in September from 86% in August, after the Hoskote cold-chain hub went live."
    },
    {
      "id": "KB-108",
      "title": "[SYNTHETIC] Competitive Price Tracker, Bengaluru Chilled Bay, September 2026",
      "fact": "Hershey's 200ml milkshake retails at ₹45 with 5g protein and Sofit 200ml soya at ₹55 with 7g protein, against Protiva 200ml at ₹70 with 20g protein, giving Protiva the lowest cost per gram of protein in the bay at ₹3.50 versus ₹9.00 and ₹7.86."
    },
    {
      "id": "KB-109",
      "title": "[SYNTHETIC] Chilled Salad Shrink Review, South India, September 2026",
      "fact": "Chilled salad shrink averaged 6.1% of units dispatched on a 4-day shelf life, falling to 2.4% in stores taking daily rather than alternate-day drops."
    },
    {
      "id": "KB-110",
      "title": "[SYNTHETIC] Share of Shelf Benchmark, Chilled Protein Bay, Q3 2026",
      "fact": "Stores holding at least 30% share of shelf in the chilled protein bay recorded 19% higher brand throughput than stores under 20% share, measured across 22 comparable urban stores."
    },
    {
      "id": "KB-200",
      "publisher": "Int. Journal of Retail and Distribution Management",
      "published": "May 2026",
      "url": "https://doi.org/10.1108/IJRDM-09-2025-0758",
      "title": "[VERIFIED] Corsten, Gruen and LaBrecque, Beyond Technology: What Differentiates On-Shelf Availability Performance in Retail",
      "fact": "Across a survey of 55 international grocery and non-grocery consumables retailers, out-of-stock levels stubbornly remain about 8% despite rising investment in shelf-visibility technology, against a recommended 95% on-shelf availability target."
    },
    {
      "id": "KB-201",
      "publisher": "arXiv preprint",
      "published": "June 2026",
      "url": "https://arxiv.org/abs/2506.05357",
      "title": "[VERIFIED] Rekik, Oliva, Glock and Syntetos, Inventory Record Inaccuracy in Grocery Retailing",
      "fact": "Across roughly 24,000 SKUs in 11 grocery stores, performing an inventory audit led to an 11% store-wide sales lift, with the entire lift concentrated on items where system inventory exceeded actual inventory."
    },
    {
      "id": "KB-202",
      "publisher": "arXiv preprint",
      "published": "June 2026",
      "url": "https://arxiv.org/abs/2506.05357",
      "title": "[VERIFIED] Rekik, Oliva, Glock and Syntetos, Inventory Record Inaccuracy in Grocery Retailing",
      "fact": "Inventory record inaccuracy rose with average inventory level, restocking frequency and perishability, and the sales benefit of auditing was most pronounced on perishable items."
    },
    {
      "id": "KB-203",
      "publisher": "NielsenIQ",
      "published": "June 2025",
      "url": "https://nielseniq.com/global/en/news-center/2025/niq-indian-consumers-are-taking-charge-of-their-health-through-smarter-food-and-tech-choices/",
      "title": "[VERIFIED] NielsenIQ Global State of Health and Wellness 2025, India release",
      "fact": "51% of Indian consumers say they struggle to find healthier alternatives in the market, and the same 51% say those alternatives are too expensive."
    },
    {
      "id": "KB-204",
      "publisher": "NielsenIQ",
      "published": "June 2025",
      "url": "https://nielseniq.com/global/en/news-center/2025/niq-indian-consumers-are-taking-charge-of-their-health-through-smarter-food-and-tech-choices/",
      "title": "[VERIFIED] NielsenIQ Global State of Health and Wellness 2025, India release",
      "fact": "Over the next 12 months 49% of Indian consumers plan to buy more high-fibre foods and 37% plan to add more plant-based protein, from a survey of nearly 19,000 adult grocery shoppers across 19 countries."
    },
    {
      "id": "KB-205",
      "publisher": "NielsenIQ",
      "published": "March 2026",
      "url": "https://nielseniq.com/global/en/news-center/2026/niq-gst-2-0-transition-reshapes-indias-fmcg-growth-landscape/",
      "title": "[VERIFIED] NielsenIQ India fast-moving consumer goods Quarterly Snapshot, October to December 2025",
      "fact": "E-commerce reached 18% of fast-moving consumer goods sales in the top 8 Indian metros and has passed 21% in southern metros, with quick commerce accounting for over three-quarters of all e-commerce fast-moving consumer goods sales."
    },
    {
      "id": "KB-206",
      "publisher": "NielsenIQ",
      "published": "March 2026",
      "url": "https://nielseniq.com/global/en/news-center/2026/niq-gst-2-0-transition-reshapes-indias-fmcg-growth-landscape/",
      "title": "[VERIFIED] NielsenIQ India fast-moving consumer goods Quarterly Snapshot, October to December 2025",
      "fact": "The Indian fast-moving consumer goods sector recorded value growth of 7.8% year on year in the October to December 2025 quarter."
    },
    {
      "id": "KB-207",
      "publisher": "NielsenIQ",
      "published": "May 2025",
      "url": "https://nielseniq.com/global/en/insights/analysis/2025/fmcg-growth-momentum-shifts-rural-india-and-small-players-take-charge/",
      "title": "[VERIFIED] NielsenIQ India fast-moving consumer goods Quarterly Snapshot, January to March 2025",
      "fact": "In Indian metros modern trade held 22.8% channel share, down 2.8 points year on year, while e-commerce volume grew 39.9% as modern trade volume fell 7.7%."
    },
    {
      "id": "KB-208",
      "publisher": "Bain and Company with Flipkart",
      "published": "April 2026",
      "url": "https://www.bain.com/insights/how-india-shops-online-2026/",
      "title": "[VERIFIED] Bain and Company with Flipkart, How India Shops Online 2026",
      "fact": "Indian e-grocery penetration grew roughly fivefold to reach 1.5% of the overall grocery market in 2025, while quick commerce GMV doubled annually since 2023 to 10 to 11 billion dollars."
    },
    {
      "id": "KB-209",
      "publisher": "NielsenIQ",
      "published": "August 2025",
      "url": "https://nielseniq.com/global/en/news-center/2025/rural-fuels-indias-13-9-fmcg-growth-in-q2-while-urban-recovery-gains-momentum/",
      "title": "[VERIFIED] NielsenIQ India fast-moving consumer goods Quarterly Snapshot, April to June 2025",
      "fact": "E-commerce is already delivering more than half of omnichannel fast-moving consumer goods growth in India, and southern metros lead on e-commerce share at 18.4% against 15.8% across the eight metros."
    },
    {
      "id": "KB-210",
      "publisher": "Eternal Limited",
      "published": "January 2026",
      "url": "https://www.eternal.com/blog/q3fy26/",
      "title": "[VERIFIED] Eternal Limited Q3 FY26 Shareholders Letter",
      "fact": "Quick commerce net order value at Blinkit grew 121% year on year in the quarter to December 2025, after 127% and 137% in the two preceding quarters, and the business turned adjusted-EBITDA profitable for the first time."
    }
  ],
  "planogram": {
    "id": "PG-Q4-2026-CP",
    "name": "October to December 2026 Chilled Protein Reset, Modern Trade Urban",
    "bay": "Aisle 2, Bay 4, Chilled Protein and Dairy Drinks",
    "standard": "Picture of Success retail execution convention, scored on on-shelf availability and share of shelf",
    "shelfLevels": "5 shelves. Shelf 1 stretch, shelf 2 eye level, shelf 3 hand level, shelf 4 stoop, shelf 5 floor",
    "totalBayFacings": 44,
    "assignedFacings": 13,
    "sosTargetPct": 30,
    "minFacingsPerSKU": 2,
    "ourBrands": [
      "Protiva"
    ],
    "competitorBrands": [
      "Hershey's",
      "Sofit",
      "store private label"
    ],
    "executionNote": "The fourth-quarter reset assigns Protiva 13 of 44 facings. Last audit found 0 executed. Competitors hold the bay.",
    "rules": [
      {
        "code": "OSA",
        "rule": "On-shelf availability",
        "spec": "Every Protiva product assigned to this bay is physically present with at least one facing. Report any assigned product with no facing, and say what occupies the slot instead."
      },
      {
        "code": "NOF",
        "rule": "Number of facings",
        "spec": "Each present Protiva product holds at least the 2-facing minimum, and the brand holds 13 facings in total as assigned by the reset."
      },
      {
        "code": "SOS",
        "rule": "Share of shelf",
        "spec": "Protiva holds at least 30 percent of the 44 visible facings in this bay. State the percentage you estimate for Protiva and for each competitor. The 30 percent figure is a commercial target negotiated with the retailer, not a researched optimum."
      },
      {
        "code": "POS",
        "rule": "Position accuracy",
        "spec": "Each product sits on the shelf level the planogram specifies, not merely somewhere in the bay. The 200ml shakes and the 330ml high-protein shake belong at eye level on shelf 2, Vanilla at hand level on shelf 3."
      },
      {
        "code": "BLK",
        "rule": "Brand block integrity",
        "spec": "Each brand is blocked contiguously as a vertical block, with no competing brand interleaved inside another brand's block."
      },
      {
        "code": "PRC",
        "rule": "Price compliance",
        "spec": "Every visible product carries a legible price tag on the shelf edge, aligned directly beneath the correct product, showing the current shelf price. The price ladder across pack sizes reads correctly."
      },
      {
        "code": "PRM",
        "rule": "Promotion execution",
        "spec": "Point-of-sale material for every active promotion in this bay is present, current, and sited with the promoted product."
      },
      {
        "code": "CND",
        "rule": "Product condition",
        "spec": "All packs front-faced and undamaged. No crushed, bloated, leaking or out-of-date packs on shelf."
      }
    ],
    "skuIds": [
      "R01",
      "R02",
      "R03",
      "R04"
    ],
    "promoNames": [
      "Protein Pledge Bundle"
    ]
  },
  "benchmark": {
    "id": "BM-CHILLED-01",
    "name": "Competitor benchmark, observed execution of the bay leader",
    "bay": "Aisle 2, Bay 4, Chilled Protein and Dairy Drinks",
    "brand": "Hershey's",
    "standard": "observed execution only; this is not compliance with Hershey's own planogram, which is not known",
    "shelfLevels": "5 shelves. Shelf 1 stretch, shelf 2 eye level, shelf 3 hand level, shelf 4 stoop, shelf 5 floor",
    "rules": [
      {
        "code": "PRS",
        "rule": "Presence",
        "spec": "Hershey's products are physically on this shelf. Name each flavour or variant you can identify."
      },
      {
        "code": "DEP",
        "rule": "Facing depth",
        "spec": "Each Hershey's variant you can identify holds at least 2 facings side by side."
      },
      {
        "code": "SOS",
        "rule": "Share of shelf",
        "spec": "Hershey's holds the largest share of visible facings of any single brand in the bay. State your estimated percentage for Hershey's and for each other brand."
      },
      {
        "code": "EYE",
        "rule": "Eye-level presence",
        "spec": "Hershey's occupies shelf 2 (eye level) or shelf 3 (hand level), not only the stoop or floor shelves."
      },
      {
        "code": "BLK",
        "rule": "Brand block integrity",
        "spec": "Hershey's sits as one contiguous block, with no other brand interleaved inside it."
      },
      {
        "code": "PRC",
        "rule": "Price tags",
        "spec": "Hershey's products carry legible shelf-edge price tags aligned beneath the correct product. Quote what a tag reads."
      },
      {
        "code": "CND",
        "rule": "Product condition",
        "spec": "Hershey's packs are front-faced and undamaged, with no crushed, tilted or rear-faced packs."
      }
    ]
  },
  "kpis": {
    "revenueTarget": 420000,
    "conversionRate": 0.68,
    "returnCustomerPct": 0.72,
    "nps": 61,
    "totalSKUs": 847
  },
  "asOfDate": "2026-10-22"
};
