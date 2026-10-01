// RetailIQ — synthetic demo dataset (all values clearly labelled SYNTHETIC)
// In production: replace with BigQuery API calls via Cloud Run backend

const RETAIL_DATA = {

  // ── Store & Brand ──────────────────────────────────────────────────────────
  store: {
    name: "FreshMart Express — Koramangala",
    city: "Bengaluru",
    zone: "South India",
    storeId: "BLR-KOR-014",
    sqft: 4200,
    segment: "Urban Grocery",
    openDate: "2021-03-15",
  },

  // ── Categories & Products ─────────────────────────────────────────────────
  categories: ["Dairy & Eggs", "Snacks & Beverages", "Fresh Produce", "Packaged Foods", "Personal Care"],

  products: [
    { id:"P001", name:"Amul Gold Milk 1L",       cat:"Dairy & Eggs",        price:68,  stock:142, reorderAt:40, unitsSoldLast30d:1240, margin:0.09, trending:true, ours:false },
    { id:"P002", name:"Lay's Classic Salted 90g", cat:"Snacks & Beverages",  price:20,  stock:88,  reorderAt:30, unitsSoldLast30d:890,  margin:0.22, trending:false, ours:false },
    { id:"P003", name:"Tropicana Orange 1L",      cat:"Snacks & Beverages",  price:130, stock:34,  reorderAt:25, unitsSoldLast30d:410,  margin:0.18, trending:false, ours:false },
    { id:"P004", name:"Britannia NutriChoice",    cat:"Packaged Foods",      price:45,  stock:12,  reorderAt:20, unitsSoldLast30d:670,  margin:0.20, trending:true, ours:true },
    { id:"P005", name:"Dove Soap 100g",           cat:"Personal Care",       price:60,  stock:56,  reorderAt:15, unitsSoldLast30d:320,  margin:0.28, trending:false, ours:false },
    { id:"P006", name:"Farm Fresh Tomatoes 1kg",  cat:"Fresh Produce",       price:40,  stock:95,  reorderAt:30, unitsSoldLast30d:1100, margin:0.15, trending:true, ours:false },
    { id:"P007", name:"Haldiram Bhujia 400g",     cat:"Snacks & Beverages",  price:110, stock:67,  reorderAt:20, unitsSoldLast30d:540,  margin:0.21, trending:false, ours:false },
    { id:"P008", name:"Nescafe Classic 200g",     cat:"Packaged Foods",      price:395, stock:28,  reorderAt:15, unitsSoldLast30d:190,  margin:0.25, trending:true, ours:true },
    { id:"P009", name:"Amul Butter 500g",         cat:"Dairy & Eggs",        price:275, stock:41,  reorderAt:20, unitsSoldLast30d:380,  margin:0.11, trending:false, ours:false },
    { id:"P010", name:"Sunfeast Marie Light",     cat:"Packaged Foods",      price:30,  stock:8,   reorderAt:25, unitsSoldLast30d:820,  margin:0.19, trending:false, ours:true },
    { id:"P011", name:"Hershey's Milkshake Vanilla 200ml", cat:"Dairy & Eggs", price:45, stock:118, reorderAt:40, unitsSoldLast30d:960,  margin:0.24, trending:true, ours:true },
    { id:"P012", name:"Hershey's Milkshake Cookies 200ml", cat:"Dairy & Eggs", price:45, stock:74,  reorderAt:40, unitsSoldLast30d:710,  margin:0.24, trending:true, ours:true },
    { id:"P013", name:"Sofit Soya Almond 200ml",  cat:"Dairy & Eggs",        price:35,  stock:62,  reorderAt:30, unitsSoldLast30d:480,  margin:0.26, trending:false, ours:true },
  ],

  // ── Revenue (last 7 days, daily totals in ₹) ────────────────────────────
  // revenue = transactions x that day's average basket, so the KPI tiles below
  // derive from this table rather than contradicting it.
  revenueWeek: [
    { day:"Mon", revenue:212160, transactions:312 },
    { day:"Tue", revenue:184870, transactions:278 },
    { day:"Wed", revenue:240810, transactions:349 },
    { day:"Thu", revenue:195552, transactions:291 },
    { day:"Fri", revenue:315135, transactions:447 },
    { day:"Sat", revenue:429364, transactions:598 },
    { day:"Sun", revenue:446424, transactions:627 },
  ],

  // ── Demand Forecast (next 7 days) ────────────────────────────────────────
  forecast: [
    { day:"Mon", predicted:208000, lower:186000, upper:230000 },
    { day:"Tue", predicted:195000, lower:174000, upper:216000 },
    { day:"Wed", predicted:249000, lower:224000, upper:274000 },
    { day:"Thu", predicted:218000, lower:195000, upper:241000 },
    { day:"Fri", predicted:322000, lower:290000, upper:354000 },
    { day:"Sat", predicted:431000, lower:389000, upper:473000 },
    { day:"Sun", predicted:444000, lower:401000, upper:487000 },
  ],

  // ── Customer Segments ────────────────────────────────────────────────────
  segments: [
    { name:"Weekend Warriors",  pct:34, avgBasket:1150, visits:1.4, desc:"Bulk-buy on weekends, high-value baskets" },
    { name:"Daily Top-Ups",     pct:28, avgBasket:330,  visits:5.8, desc:"Small daily purchases, highly loyal" },
    { name:"Deal Seekers",      pct:22, avgBasket:620,  visits:2.1, desc:"Price-sensitive, respond to promotions" },
    { name:"Convenience First", pct:16, avgBasket:575,  visits:2.9, desc:"Time-pressed, value speed & availability" },
  ],

  // ── Inventory Alerts ─────────────────────────────────────────────────────
  alerts: [
    { product:"Sunfeast Marie Light",     level:"critical", stock:8,  reorderAt:25, action:"Reorder 200 units TODAY" },
    { product:"Britannia NutriChoice",    level:"critical", stock:12, reorderAt:20, action:"Reorder 150 units TODAY" },
    { product:"Tropicana Orange 1L",      level:"warning",  stock:34, reorderAt:25, action:"Reorder within 2 days" },
    { product:"Nescafe Classic 200g",     level:"warning",  stock:28, reorderAt:15, action:"Monitor — trending up" },
  ],

  // ── Promotions Active ────────────────────────────────────────────────────
  promotions: [
    { name:"Weekend Bonanza", discount:"15% off Snacks", validity:"Fri–Sun", uplift:"+22% category sales", skuIds:["P002","P007"] },
    { name:"Dairy Deal",      discount:"Buy 2 Hershey's Milkshake 200ml, get ₹10 off", validity:"All week", uplift:"+11% dairy", skuIds:["P011","P012"] },
    { name:"Health Week",     discount:"10% off NutriChoice & Marie", validity:"Mon–Thu", uplift:"+18% packaged", skuIds:["P004","P010"] },
  ],

  // ── Shopper Persona Catalogue (for conversational assistant) ─────────────
  shopperProfiles: [
    {
      id:"S1", name:"Priya", age:32, role:"Software Engineer",
      preferences:["organic", "low-sugar", "quick meals"],
      recentBuys:["Farm Fresh Tomatoes", "Amul Gold Milk", "Nescafe Classic"],
      basket:["Amul Gold Milk 1L", "Farm Fresh Tomatoes 1kg"],
    },
    {
      id:"S2", name:"Rahul", age:45, role:"Business Owner",
      preferences:["bulk", "value packs", "household staples"],
      recentBuys:["Amul Butter 500g", "Haldiram Bhujia 400g", "Sunfeast Marie Light"],
      basket:[],
    },
    {
      id:"S3", name:"Guest Shopper", age:null, role:null,
      preferences:[], recentBuys:[], basket:[],
    },
  ],

  // ══ SALES REP SURFACE ═════════════════════════════════════════════════════

  rep: {
    name: "Anita Sharma", role: "Territory Sales Executive",
    territory: "Bengaluru South", employeeId: "TSE-4417",
    quotaMonth: 2400000, achievedMonth: 1812000, visitsPlanned: 22, visitsDone: 14,
    monthDaysTotal: 31, monthDaysElapsed: 22,
  },

  // ── Target tracking (the "track targets" ask) ─────────────────────────────
  targets: {
    period: "October 2026",
    byAccount: [
      { account:"FreshMart Express",   target:1400000, achieved:1095000 },
      { account:"DailyNeeds Supermart", target:700000,  achieved:462000  },
      { account:"General Trade (misc)", target:300000,  achieved:255000  },
    ],
    byCategory: [
      { cat:"Dairy & Eggs",       target:820000, achieved:698000, focus:true  },
      { cat:"Packaged Foods",     target:640000, achieved:401000, focus:true  },
      { cat:"Snacks & Beverages", target:560000, achieved:480000, focus:false },
      { cat:"Personal Care",      target:380000, achieved:233000, focus:false },
    ],
    mustWinSKUs: [
      { name:"Britannia NutriChoice",            target:900, achieved:512 },
      { name:"Hershey's Milkshake Vanilla 200ml", target:1200, achieved:1104 },
      { name:"Nescafe Classic 200g",             target:400, achieved:191 },
    ],
  },

  // ── Visit plan (the "schedule visits" ask) ────────────────────────────────
  // priority is computed, not hand-set: see computePriority() in index.html
  visitPlan: [
    { store:"FreshMart Express — Koramangala",  storeId:"BLR-KOR-014", account:"FreshMart Express",
      daysSince:41, cadenceDays:6,  openTasks:4, revenueAtRisk:142000, targetGap:305000, scheduled:"2026-10-22 10:30" },
    { store:"DailyNeeds Supermart — Jayanagar", storeId:"BLR-JAY-007", account:"DailyNeeds Supermart",
      daysSince:13, cadenceDays:14, openTasks:2, revenueAtRisk:86000,  targetGap:238000, scheduled:"2026-10-23 14:00" },
    { store:"FreshMart Express — HSR Layout",   storeId:"BLR-HSR-021", account:"FreshMart Express",
      daysSince:9,  cadenceDays:6,  openTasks:1, revenueAtRisk:118000, targetGap:305000, scheduled:null },
    { store:"DailyNeeds Supermart — BTM",       storeId:"BLR-BTM-033", account:"DailyNeeds Supermart",
      daysSince:22, cadenceDays:14, openTasks:3, revenueAtRisk:74000,  targetGap:238000, scheduled:null },
    { store:"FreshMart Express — Indiranagar",  storeId:"BLR-IND-008", account:"FreshMart Express",
      daysSince:4,  cadenceDays:6,  openTasks:0, revenueAtRisk:96000,  targetGap:305000, scheduled:null },
    { store:"DailyNeeds Supermart — Banashankari", storeId:"BLR-BAN-019", account:"DailyNeeds Supermart",
      daysSince:31, cadenceDays:14, openTasks:2, revenueAtRisk:58000,  targetGap:238000, scheduled:null },
  ],

  // ── Manager view: the team (rep-wise performance + coverage + coaching) ──
  team: [
    { name:"Anita Sharma",   territory:"Bengaluru South", quota:2400000, achieved:1812000,
      visitsPlanned:22, visitsDone:14, outletsCovered:18, outletsTotal:24,
      avgPitchScore:71, rehearsalsDone:9, complianceRate:0.82, strikeRate:0.58 },
    { name:"Rohit Menon",    territory:"Bengaluru East",  quota:2200000, achieved:2046000,
      visitsPlanned:20, visitsDone:19, outletsCovered:21, outletsTotal:22,
      avgPitchScore:84, rehearsalsDone:16, complianceRate:0.91, strikeRate:0.72 },
    { name:"Kavya Reddy",    territory:"Bengaluru North", quota:2000000, achieved:1180000,
      visitsPlanned:20, visitsDone:11, outletsCovered:12, outletsTotal:23,
      avgPitchScore:54, rehearsalsDone:2,  complianceRate:0.64, strikeRate:0.39 },
    { name:"Imran Qureshi",  territory:"Bengaluru West",  quota:2100000, achieved:1743000,
      visitsPlanned:21, visitsDone:16, outletsCovered:17, outletsTotal:21,
      avgPitchScore:68, rehearsalsDone:7,  complianceRate:0.79, strikeRate:0.55 },
  ],

  // ── Marketing insights pushed to the rep (kills the marketing silo) ──────
  marketing: [
    { title:"Health Week national campaign goes live 3 Nov", type:"Campaign",
      detail:"TV and digital burst on health biscuits for 3 weeks from 3 November. Expect category pull in urban modern trade. Secure end-cap space before launch, not after.",
      relevance:"Directly supports the NutriChoice 6-pack relist ask at FreshMart." },
    { title:"Flavoured milk is the fastest growing dairy sub-category", type:"Category signal",
      detail:"27% YoY growth in South India modern trade, with 200ml single-serve driving 71% of it.",
      relevance:"Use in the dairy beverage bay conversation. Supports a facings increase ask." },
    { title:"Competitor launched a 6-pack at Rs 42 in Bengaluru", type:"Competitive alert",
      detail:"Priced 7% below our 6-pack. Early listing seen in 4 modern trade chains, not yet at FreshMart.",
      relevance:"Pre-empt at FreshMart. Lead with the 20% margin and Q4 rebate, not with price." },
    { title:"Shopper search demand: 'low sugar' up 34% in app queries", type:"Consumer signal",
      detail:"Derived from the shopper assistant's own query logs across the territory over 30 days.",
      relevance:"Evidence that health positioning is pulling, not just being pushed." },
  ],

  // Retail accounts the rep sells INTO (we are the brand/CPG side)
  accounts: [
    {
      id:"ACC-01", name:"FreshMart Express", type:"Modern Trade — Urban Grocery",
      stores:14, tier:"Platinum", relationship:"7 years",
      ytdValue:18400000, growthYoY:0.12,
      contact:{ name:"Vikram Rao", role:"Category Buyer — Packaged Foods", style:"Data-driven, margin-focused, time-pressed" },
    },
    {
      id:"ACC-02", name:"DailyNeeds Supermart", type:"Modern Trade — Value Format",
      stores:31, tier:"Gold", relationship:"3 years",
      ytdValue:9200000, growthYoY:-0.04,
      contact:{ name:"Meera Iyer", role:"Regional Merchandising Head", style:"Price-sensitive, wants promo support, sceptical of new SKUs" },
    },
  ],

  // Specific store visits on the rep's plan
  visits: [
    {
      id:"V-00118", accountId:"ACC-01", store:"FreshMart Express — Koramangala", storeId:"BLR-KOR-014",
      date:"2026-10-22", time:"10:30", duration:"90 min", status:"scheduled",
      lastVisit:"2026-09-11", daysSince:41, visitFrequency:"every 5-7 days (Index Score based)",
      objective:"Recover the NutriChoice 6-pack listing and secure end-cap for Health Week",
      openTasks:[
        "Audit the dairy beverage bay against the Q4 planogram reset",
        "Close pending audit on 4 assets (chillers BLR-KOR-014-C1 to C4)",
        "Collect signed planogram acknowledgement for Q4 reset",
        "Present Nescafe Classic 200g margin case",
      ],
      history:{
        lastOrderValue:142000, ordersLast6m:7, avgOrderValue:128000,
        listingsLost:["Britannia NutriChoice 6-pack (delisted Jul 2026)"],
        pastObjections:[
          "Your NutriChoice 6-pack moved 40% slower than the single pack last quarter, why should I relist it?",
          "Nescafe at Rs 395 is Rs 20 above the competing SKU and my margin is thinner.",
          "I only have one end-cap free and three brands are asking for it.",
        ],
      },
    },
    {
      id:"V-00119", accountId:"ACC-02", store:"DailyNeeds Supermart — Jayanagar", storeId:"BLR-JAY-007",
      date:"2026-10-23", time:"14:00", duration:"60 min", status:"scheduled",
      lastVisit:"2026-10-09", daysSince:13, visitFrequency:"every 14 days",
      objective:"Arrest the -4% YoY decline, push value packs ahead of festive season",
      openTasks:["Resolve 2 short-supply complaints","Re-negotiate shelf share in Snacks bay"],
      history:{
        lastOrderValue:86000, ordersLast6m:5, avgOrderValue:91000,
        listingsLost:[],
        pastObjections:[
          "Your fill rate dropped to 82% last month, I lost sales because of you.",
          "DailyNeeds shoppers want value packs, your portfolio is premium-heavy.",
        ],
      },
    },
  ],

  // Knowledge base — every pitch proof point must cite one of these
  kbDocs: [
    { id:"KB-101", title:"[SYNTHETIC] Nielsen Retail Audit — South India Biscuits Q3 2026",
      fact:"Health-positioned biscuits grew 18.4% YoY in South India modern trade, versus 3.1% for the total biscuit category." },
    { id:"KB-102", title:"[SYNTHETIC] FreshMart Koramangala — Category Performance Report Aug 2026",
      fact:"Packaged Foods contributed 22% of store revenue but only 14% of shelf space, the widest gap of any category." },
    { id:"KB-103", title:"[SYNTHETIC] Internal Margin Sheet — Q4 2026 Trade Terms",
      fact:"NutriChoice 6-pack carries a 20% retailer margin versus 19% on the single pack, with a 4% Q4 volume rebate above 500 units." },
    { id:"KB-104", title:"[SYNTHETIC] Shopper Panel Study — Bengaluru Urban, Jul 2026",
      fact:"63% of urban Bengaluru shoppers buying health biscuits purchase multipacks when placed at eye level, versus 31% at bottom shelf." },
    { id:"KB-105", title:"[SYNTHETIC] Health Week Campaign Post-Mortem — Mar 2026",
      fact:"The Health Week end-cap delivered an 18% category uplift at 6 comparable FreshMart stores, with zero cannibalisation of the single pack." },
    { id:"KB-106", title:"[SYNTHETIC] Supply Chain Scorecard — Sep 2026",
      fact:"Fill rate recovered to 96.2% in September after the Hosur depot expansion, up from 82% in August." },
    { id:"KB-107", title:"[SYNTHETIC] Coffee Category Tracker — Sep 2026",
      fact:"Nescafe Classic 200g holds 34% value share and 25% retailer margin, the highest margin SKU in the instant coffee bay." },
    { id:"KB-108", title:"[SYNTHETIC] Flavoured Milk Category Review — South India, Sep 2026",
      fact:"Flavoured milk grew 27% YoY in South India modern trade, the fastest growing dairy sub-category, with 200ml single-serve driving 71% of that growth." },
    { id:"KB-109", title:"[SYNTHETIC] Planogram Compliance Benchmark — Q3 2026",
      fact:"Stores holding full planogram compliance in the dairy beverage bay averaged 14% higher category throughput than non-compliant stores in the same cluster." },
  ],

  // Planogram spec used for compliance scoring.
  // Rules follow the standard CPG retail-execution model: the 5P Picture of
  // Success (Product, Placement, Price, Promotion, POSM) measured against the
  // two headline industry KPIs, On-Shelf Availability and Share of Shelf.
  planogram: {
    id:"PG-Q4-2026", name:"Q4 2026 Dairy Beverages Reset — Modern Trade Urban",
    bay:"Aisle 2, Bay 4 — Flavoured Milk & Dairy Beverages",
    standard:"PicOS 5P retail execution standard, scored on OSA and Share of Shelf",
    // Standard modern-trade gondola: 5 shelves, named by shopper reach zone.
    shelfLevels:"5 shelves. Shelf 1 stretch, shelf 2 eye level, shelf 3 hand level, shelf 4 stoop, shelf 5 floor",
    sosTargetPct: 40,
    minFacingsPerSKU: 2,
    // Stated explicitly rather than inferred from SKU names, so the audit does
    // not mistake our own second brand for a competitor.
    ourBrands: ["Hershey's", "Sofit"],
    rules: [
      { code:"OSA", rule:"On-shelf availability",
        spec:"Every must-stock SKU is physically present with at least one facing. No empty gap anywhere a must-stock SKU is planogrammed." },
      { code:"SOS", rule:"Share of shelf",
        spec:"Our brand block holds at least 40 percent of the visible facings in this bay, and every must-stock SKU holds at least 2 facings." },
      { code:"PLC", rule:"Placement level",
        spec:"Premium flavoured milk occupies eye level, shelf 2. Soya and value packs occupy hand level or below, shelf 3 to 5." },
      { code:"BLK", rule:"Brand block integrity",
        spec:"All variants of one brand are blocked contiguously as a vertical block, with no competitor SKU interleaved inside the block." },
      { code:"PRC", rule:"Price compliance",
        spec:"Every visible SKU carries a legible price tag on the shelf edge, aligned directly beneath the correct product, showing the current shelf price." },
      { code:"PRM", rule:"Promotion execution",
        spec:"Point-of-sale material for every active promotion in this bay is present, current, and sited with the promoted SKU." },
      { code:"CND", rule:"Product condition",
        spec:"All packs front-faced and undamaged. No crushed, bloated, leaking or out-of-date packs on shelf." },
    ],
    // SKUs the planogram actually assigns to this bay. Used as the expected list
    // for the audit, so the model is not asked to find butter on a milk shelf.
    skuIds: ["P011","P012","P013"],
    // Only promotions whose point-of-sale material belongs in this bay.
    promoNames: ["Dairy Deal"],
  },

  // ── KPIs ─────────────────────────────────────────────────────────────────
  kpis: {
    revenueTarget: 420000,
    conversionRate: 0.68,
    returnCustomerPct: 0.72,
    nps: 61,
    totalSKUs: 847,
  },
};
