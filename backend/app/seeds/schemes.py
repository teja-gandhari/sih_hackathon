import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import AsyncSessionLocal, engine, Base
from app.models.business import BusinessSector, BusinessType
from app.models.scheme import GovernmentScheme


SECTORS_DATA = [
    {
        "code": "dairy",
        "name_en": "Dairy & Animal Husbandry",
        "name_te": "పాడి పరిశ్రమ & పశుపోషణ",
        "name_hi": "डेयरी और पशुपालन",
        "description": "Milch animals, mini dairy units, bulk milk chilling and dairy value addition",
        "icon_name": "local_shipping",
        "business_types": [
            {
                "code": "dairy_5_murrah",
                "name_en": "5 Murrah Buffalo Dairy Unit",
                "name_te": "5 ముర్రా గేదెల డెయిరీ యూనిట్",
                "name_hi": "5 मुर्रा भैंस डेयरी इकाई",
                "unit_label": "Animals",
                "default_scale": 5,
                "default_capex": 350000.0,
                "default_monthly_opex": 22000.0,
                "default_monthly_revenue": 38000.0,
                "typical_ticket_size": 45.0,  # Milk per liter
                "min_purchasing_power_tier": "low",
                "requires_daily_footfall": False,
                "is_export_or_wholesale": True,  # Sold to dairy cooperative / collection center
                "seasonal_cyclical": True,
                "capex_breakdown": {
                    "animals_cost": 275000.0,
                    "cattle_shed": 50000.0,
                    "milking_equipment": 25000.0
                },
                "opex_breakdown": {
                    "green_fodder_and_feed": 16000.0,
                    "veterinary_and_medicines": 2500.0,
                    "labor_and_electricity": 3500.0
                }
            }
        ]
    },
    {
        "code": "food_processing",
        "name_en": "Food Processing & Agri Mills",
        "name_te": "ఆహార ప్రాసెసింగ్ & మిల్లులు",
        "name_hi": "खाद्य प्रसंस्करण और आटा/दाल मिल",
        "description": "Mini flour mills, spice grinding, cold press oil expellers, and pulse mills",
        "icon_name": "inventory_2",
        "business_types": [
            {
                "code": "spice_grinding_unit",
                "name_en": "Automatic Spice Grinding & Packaging Unit",
                "name_te": "మసాలా దినుసుల గ్రైండింగ్ & ప్యాకేజింగ్ యూనిట్",
                "name_hi": "मसाला पिसाई और पैकेजिंग यूनिट",
                "unit_label": "Kg/Day",
                "default_scale": 100,
                "default_capex": 280000.0,
                "default_monthly_opex": 25000.0,
                "default_monthly_revenue": 45000.0,
                "typical_ticket_size": 50.0,  # ₹50 per 200g spice packet
                "min_purchasing_power_tier": "lower_middle",
                "requires_daily_footfall": False,
                "is_export_or_wholesale": False,
                "seasonal_cyclical": False,
                "capex_breakdown": {
                    "pulverizer_machine": 150000.0,
                    "band_sealing_packaging_machine": 60000.0,
                    "storage_and_electricals": 70000.0
                },
                "opex_breakdown": {
                    "raw_spices_procurement": 18000.0,
                    "packaging_pouches": 3000.0,
                    "electricity_and_misc": 4000.0
                }
            }
        ]
    },
    {
        "code": "retail",
        "name_en": "Rural Retail & Kirana Store",
        "name_te": "గ్రామీణ కిరాణా & జనరల్ స్టోర్",
        "name_hi": "ग्रामीण किराना और जनरल स्टोर",
        "description": "Daily grocery essentials, FMCG, and agro-input retail stores",
        "icon_name": "storefront",
        "business_types": [
            {
                "code": "village_kirana_fmcg",
                "name_en": "Village General Kirana & FMCG Store",
                "name_te": "గ్రామ కిరాణా & నిత్యావసర వస్తువుల దుకాణం",
                "name_hi": "ग्राम किराना और दैनिक आवश्यकता स्टोर",
                "unit_label": "Sqft",
                "default_scale": 300,
                "default_capex": 200000.0,
                "default_monthly_opex": 15000.0,
                "default_monthly_revenue": 32000.0,
                "typical_ticket_size": 35.0,  # Daily small purchase
                "min_purchasing_power_tier": "low",
                "requires_daily_footfall": True,
                "is_export_or_wholesale": False,
                "seasonal_cyclical": False,
                "capex_breakdown": {
                    "display_racks_and_counters": 60000.0,
                    "initial_inventory_stock": 120000.0,
                    "pos_billing_machine": 20000.0
                },
                "opex_breakdown": {
                    "shop_rent": 4000.0,
                    "transport_and_logistics": 3500.0,
                    "electricity_and_packaging": 2500.0,
                    "inventory_replenishment": 5000.0
                }
            }
        ]
    },
    {
        "code": "agriculture",
        "name_en": "Agriculture & Allied Enterprises",
        "name_te": "వ్యవసాయం & అనుబంధ రంగాలు",
        "name_hi": "कृषि और संबद्ध व्यवसाय",
        "description": "Organic vermicompost, mushroom farming, and agro-seed outlets",
        "icon_name": "agriculture",
        "business_types": [
            {
                "code": "vermicompost_unit",
                "name_en": "Commercial Vermicompost & Bio-Fertilizer Unit",
                "name_te": "వాణిజ్య వర్మీకంపోస్ట్ & సేంద్రీయ ఎరువుల యూనిట్",
                "name_hi": "व्यावसायिक वर्मीकम्पोस्ट और जैविक खाद यूनिट",
                "unit_label": "Tons/Year",
                "default_scale": 50,
                "default_capex": 180000.0,
                "default_monthly_opex": 12000.0,
                "default_monthly_revenue": 26000.0,
                "typical_ticket_size": 300.0,  # 50kg bag
                "min_purchasing_power_tier": "lower_middle",
                "requires_daily_footfall": False,
                "is_export_or_wholesale": True,
                "seasonal_cyclical": True,
                "capex_breakdown": {
                    "vermi_beds_and_shade_net": 90000.0,
                    "sieving_machine": 45000.0,
                    "earthworms_starter_stock": 45000.0
                },
                "opex_breakdown": {
                    "cow_dung_and_agri_waste": 7000.0,
                    "packing_bags": 2500.0,
                    "labor": 2500.0
                }
            }
        ]
    },
    {
        "code": "textiles",
        "name_en": "Textiles & Garment Stitching",
        "name_te": "వస్త్రాలు & కుట్టు శిక్షణ/టైలరింగ్",
        "name_hi": "वस्त्र और सिलाई केंद्र",
        "description": "Garment manufacturing, uniform stitching, embroidery, and boutique",
        "icon_name": "checkroom",
        "business_types": [
            {
                "code": "garment_stitching_center",
                "name_en": "Multi-Machine Tailoring & Garment Unit",
                "name_te": "మల్టీ మెషిన్ టైలరింగ్ & వస్త్ర యూనిట్",
                "name_hi": "मल्टी-मशीन सिलाई और गारमेंट यूनिट",
                "unit_label": "Machines",
                "default_scale": 4,
                "default_capex": 160000.0,
                "default_monthly_opex": 14000.0,
                "default_monthly_revenue": 28000.0,
                "typical_ticket_size": 150.0,
                "min_purchasing_power_tier": "lower_middle",
                "requires_daily_footfall": True,
                "is_export_or_wholesale": False,
                "seasonal_cyclical": True,  # Festival/School opening peaks
                "capex_breakdown": {
                    "industrial_sewing_machines": 100000.0,
                    "overlock_and_interlock": 35000.0,
                    "cutting_table_and_iron": 25000.0
                },
                "opex_breakdown": {
                    "threads_and_accessories": 4000.0,
                    "rent_and_power": 4000.0,
                    "helper_wages": 6000.0
                }
            }
        ]
    },
    {
        "code": "handicrafts",
        "name_en": "Handicrafts & Village Artisans",
        "name_te": "చేతివృత్తులు & గ్రామీణ కళాకారులు",
        "name_hi": "हस्तशिल्प और ग्रामीण कारीगर",
        "description": "Pottery, bamboo craft, jute bags, and decorative rural arts",
        "icon_name": "palette",
        "business_types": [
            {
                "code": "jute_eco_bags_unit",
                "name_en": "Jute & Eco-Friendly Bag Manufacturing",
                "name_te": "జనపనార ఎకో-ఫ్రెండ్లీ బ్యాగుల తయారీ",
                "name_hi": "जूट और पर्यावरण अनुकूल बैग निर्माण",
                "unit_label": "Bags/Month",
                "default_scale": 500,
                "default_capex": 140000.0,
                "default_monthly_opex": 11000.0,
                "default_monthly_revenue": 24000.0,
                "typical_ticket_size": 60.0,
                "min_purchasing_power_tier": "lower_middle",
                "requires_daily_footfall": False,
                "is_export_or_wholesale": True,
                "seasonal_cyclical": False,
                "capex_breakdown": {
                    "heavy_duty_jute_stitching_machine": 75000.0,
                    "screen_printing_setup": 35000.0,
                    "raw_jute_fabric_roll_stock": 30000.0
                },
                "opex_breakdown": {
                    "jute_cloth_and_handles": 6500.0,
                    "printing_ink": 1500.0,
                    "electricity_and_transport": 3000.0
                }
            }
        ]
    },
    {
        "code": "services",
        "name_en": "Rural Services & Tech Support",
        "name_te": "గ్రామీణ సేవా కేంద్రాలు & మొబైల్ రిపేరింగ్",
        "name_hi": "ग्रामीण सेवा केंद्र और मोबाइल रिपेयरिंग",
        "description": "Common Service Center (CSC), mobile/electronics repair, solar installation support",
        "icon_name": "build",
        "business_types": [
            {
                "code": "csc_and_mobile_repair",
                "name_en": "CSC Digital Citizen Center & Electronics Repair",
                "name_te": "డిజిటల్ సిటిజన్ సర్వీస్ సెంటర్ & మొబైల్ సర్వీసింగ్",
                "name_hi": "डिजिटल नागरिक सेवा केंद्र और मोबाइल सर्विस",
                "unit_label": "Counters",
                "default_scale": 1,
                "default_capex": 175000.0,
                "default_monthly_opex": 12000.0,
                "default_monthly_revenue": 27000.0,
                "typical_ticket_size": 40.0,  # Service fee
                "min_purchasing_power_tier": "low",
                "requires_daily_footfall": True,
                "is_export_or_wholesale": False,
                "seasonal_cyclical": False,
                "capex_breakdown": {
                    "desktop_computer_and_printer_scanner": 75000.0,
                    "mobile_soldering_and_diagnostic_station": 40000.0,
                    "inverter_ups_backup": 35000.0,
                    "shop_interior_and_branding": 25000.0
                },
                "opex_breakdown": {
                    "shop_rent": 4000.0,
                    "high_speed_internet": 1500.0,
                    "paper_and_printer_cartridges": 2500.0,
                    "spare_parts_replenishment": 4000.0
                }
            }
        ]
    }
]


SCHEMES_SEED = [
    {
        "scheme_code": "PMEGP",
        "name_en": "Prime Minister's Employment Generation Programme",
        "name_te": "ప్రధాన మంత్రి ఉపాధి కల్పన కార్యక్రమం (PMEGP)",
        "name_hi": "प्रधानमंत्री रोजगार सृजन कार्यक्रम (PMEGP)",
        "nodal_agency": "KVIC / Ministry of MSME",
        "min_project_cost": 25000.0,
        "max_project_cost": 5000000.0,
        "general_margin_pct": 10.0,
        "special_margin_pct": 5.0,
        "general_subsidy_rural_pct": 25.0,
        "general_subsidy_urban_pct": 15.0,
        "special_subsidy_rural_pct": 35.0,
        "special_subsidy_urban_pct": 25.0,
        "max_subsidy_amount": 1250000.0,
        "default_annual_interest_rate": 8.5,
        "interest_subvention_pct": 2.0,
        "max_tenure_months": 60,
        "eligible_sectors": ["dairy", "agriculture", "food_processing", "retail", "textiles", "handicrafts", "services"],
        "eligible_categories": ["general", "obc", "sc", "st", "minority", "women_entrepreneur"],
        "description_en": "Credit-linked subsidy programme providing 15% to 35% government subsidy for micro-enterprises.",
        "description_te": "సూక్ష్మ వ్యాపారాల కోసం 15% నుండి 35% వరకు ప్రభుత్వ సబ్సిడీని అందించే రుణ ఆధారిత పథకం.",
        "description_hi": "सूक्ष्म उद्यमों के लिए 15% से 35% तक सरकारी सब्सिडी प्रदान करने वाली ऋण-लिंक्ड योजना।"
    },
    {
        "scheme_code": "PMFME",
        "name_en": "PM Formalisation of Micro Food Processing Enterprises",
        "name_te": "పీఎం సూక్ష్మ ఆహార ప్రాసెసింగ్ పథకం (PMFME)",
        "name_hi": "पीएम सूक्ष्म खाद्य प्रसंस्करण उद्यम योजना (PMFME)",
        "nodal_agency": "Ministry of Food Processing Industries",
        "min_project_cost": 50000.0,
        "max_project_cost": 3000000.0,
        "general_margin_pct": 10.0,
        "special_margin_pct": 10.0,
        "general_subsidy_rural_pct": 35.0,
        "general_subsidy_urban_pct": 35.0,
        "special_subsidy_rural_pct": 35.0,
        "special_subsidy_urban_pct": 35.0,
        "max_subsidy_amount": 1000000.0,
        "default_annual_interest_rate": 8.0,
        "interest_subvention_pct": 3.0,
        "max_tenure_months": 60,
        "eligible_sectors": ["food_processing", "agriculture", "dairy"],
        "eligible_categories": ["general", "obc", "sc", "st", "minority", "women_entrepreneur"],
        "description_en": "Provides 35% credit-linked capital subsidy up to ₹10 Lakhs for food processing and agro-milling units.",
        "description_te": "ఆహార ప్రాసెసింగ్ మరియు మిల్లుల యూనిట్ల కోసం ₹10 లక్షల వరకు 35% సబ్సిడీని అందిస్తుంది.",
        "description_hi": "खाद्य प्रसंस्करण इकाइयों के लिए ₹10 लाख तक 35% क्रेडिट लिंक्ड पूंजीगत सब्सिडी प्रदान करता है।"
    },
    {
        "scheme_code": "MUDRA_KISHORE",
        "name_en": "Pradhan Mantri MUDRA Yojana (Kishore)",
        "name_te": "ప్రధాన మంత్రి ముద్ర యోజన (కిషోర్: ₹50 వేల నుండి ₹5 లక్షలు)",
        "name_hi": "प्रधानमंत्री मुद्रा योजना (किशोर: ₹50 हजार से ₹5 लाख)",
        "nodal_agency": "MUDRA / Dept of Financial Services",
        "min_project_cost": 50000.0,
        "max_project_cost": 500000.0,
        "general_margin_pct": 10.0,
        "special_margin_pct": 5.0,
        "general_subsidy_rural_pct": 0.0,
        "general_subsidy_urban_pct": 0.0,
        "special_subsidy_rural_pct": 0.0,
        "special_subsidy_urban_pct": 0.0,
        "max_subsidy_amount": 0.0,
        "default_annual_interest_rate": 8.5,
        "interest_subvention_pct": 0.0,
        "max_tenure_months": 60,
        "eligible_sectors": ["dairy", "retail", "agriculture", "food_processing", "textiles", "handicrafts", "services"],
        "eligible_categories": ["general", "obc", "sc", "st", "minority", "women_entrepreneur"],
        "description_en": "Collateral-free business loans up to ₹5 Lakhs for micro-enterprises and shopkeepers.",
        "description_te": "సూక్ష్మ వ్యాపారులు మరియు దుకాణదారుల కోసం ₹5 లక్షల వరకు హామీ లేని వ్యాపార రుణాలు.",
        "description_hi": "सूक्ष्म उद्यमियों और दुकानदारों के लिए ₹5 लाख तक का बिना गारंटी का व्यापार ऋण।"
    }
]


async def seed_sectors_and_schemes():
    """Seed initial sectors, business types, and schemes into database."""
    async with AsyncSessionLocal() as session:
        # 1. Seed Sectors & Types
        for sec in SECTORS_DATA:
            res = await session.execute(select(BusinessSector).where(BusinessSector.code == sec["code"]))
            sector_obj = res.scalars().first()
            if not sector_obj:
                sector_obj = BusinessSector(
                    code=sec["code"],
                    name_en=sec["name_en"],
                    name_te=sec["name_te"],
                    name_hi=sec["name_hi"],
                    description=sec["description"],
                    icon_name=sec["icon_name"]
                )
                session.add(sector_obj)
                await session.flush()

            for bt in sec.get("business_types", []):
                res_bt = await session.execute(select(BusinessType).where(BusinessType.code == bt["code"]))
                if not res_bt.scalars().first():
                    bt_obj = BusinessType(
                        sector_id=sector_obj.id,
                        code=bt["code"],
                        name_en=bt["name_en"],
                        name_te=bt["name_te"],
                        name_hi=bt["name_hi"],
                        unit_label=bt["unit_label"],
                        default_scale=bt["default_scale"],
                        default_capex=bt["default_capex"],
                        default_monthly_opex=bt["default_monthly_opex"],
                        default_monthly_revenue=bt["default_monthly_revenue"],
                        typical_ticket_size=bt["typical_ticket_size"],
                        min_purchasing_power_tier=bt["min_purchasing_power_tier"],
                        requires_daily_footfall=bt["requires_daily_footfall"],
                        is_export_or_wholesale=bt["is_export_or_wholesale"],
                        seasonal_cyclical=bt["seasonal_cyclical"],
                        capex_breakdown=bt["capex_breakdown"],
                        opex_breakdown=bt["opex_breakdown"]
                    )
                    session.add(bt_obj)

        # 2. Seed Schemes
        for sch in SCHEMES_SEED:
            res_sch = await session.execute(select(GovernmentScheme).where(GovernmentScheme.scheme_code == sch["scheme_code"]))
            if not res_sch.scalars().first():
                sch_obj = GovernmentScheme(
                    scheme_code=sch["scheme_code"],
                    name_en=sch["name_en"],
                    name_te=sch["name_te"],
                    name_hi=sch["name_hi"],
                    nodal_agency=sch["nodal_agency"],
                    min_project_cost=sch["min_project_cost"],
                    max_project_cost=sch["max_project_cost"],
                    general_margin_pct=sch["general_margin_pct"],
                    special_margin_pct=sch["special_margin_pct"],
                    general_subsidy_rural_pct=sch["general_subsidy_rural_pct"],
                    general_subsidy_urban_pct=sch["general_subsidy_urban_pct"],
                    special_subsidy_rural_pct=sch["special_subsidy_rural_pct"],
                    special_subsidy_urban_pct=sch["special_subsidy_urban_pct"],
                    max_subsidy_amount=sch["max_subsidy_amount"],
                    default_annual_interest_rate=sch["default_annual_interest_rate"],
                    interest_subvention_pct=sch["interest_subvention_pct"],
                    max_tenure_months=sch["max_tenure_months"],
                    eligible_sectors=sch["eligible_sectors"],
                    eligible_categories=sch["eligible_categories"],
                    description_en=sch["description_en"],
                    description_te=sch["description_te"],
                    description_hi=sch["description_hi"]
                )
                session.add(sch_obj)

        await session.commit()
        print("Successfully seeded business sectors, templates, and government schemes.")


if __name__ == "__main__":
    asyncio.run(seed_sectors_and_schemes())

