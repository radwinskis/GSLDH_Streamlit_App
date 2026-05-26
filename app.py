import streamlit as st
import ee
import geemap.foliumap as geemap
# from streamlit_folium import st_folium
import datetime as dt
from RadGEEToolbox import LandsatCollection, get_palette
import json
from google.oauth2 import service_account
import os

# ---------------------------------------------------------
# 1. Page Configuration & GEE Authentication
# ---------------------------------------------------------
st.set_page_config(page_title="GSL Dust Emission Explorer", layout="wide")
st.title("Great Salt Lake Dust Emission Explorer")

# ---------------------------------------------------------
# 1.5 Initialize Map State in Session
# ---------------------------------------------------------
# if "map_center" not in st.session_state:
#     st.session_state.map_center = [41.15, -112.5]
# if "map_zoom" not in st.session_state:
#     st.session_state.map_zoom = 9

# @st.cache_resource
# def init_gee():
#     """Authenticate and initialize GEE using the service account."""
#     try:
#         service_account = 'localpythonscripts@ut-gee-ugs-bsf-dev.iam.gserviceaccount.com'
#         credentials = ee.ServiceAccountCredentials(service_account, 'C:\\Users\\mradwin\\ut-gee-ugs-bsf-dev-53dcc5d729e0.json')
#         ee.Initialize(credentials=credentials)
#         return True
#     except Exception as e:
#         st.error(f"Failed to initialize GEE: {e}")
#         return False
# gee_ready = init_gee()

# @st.cache_resource

try:
    # 1. Get the raw string from secrets
    key_content = st.secrets["textkey"]
    
    # 2. Parse JSON with 'strict=False'
    key_dict = json.loads(key_content, strict=False)
    
    # 3. Define the mandatory Earth Engine Scope
    #    This tells Google we want access to GEE specifically
    scopes = ['https://www.googleapis.com/auth/earthengine']
    
    # 4. Create Credentials WITH Scopes
    credentials = service_account.Credentials.from_service_account_info(
        key_dict, 
        scopes=scopes
    )
    
    # 5. Initialize
    ee.Initialize(credentials=credentials)
    
except Exception as e:
    # Fallback for Local Development
    local_key_path = 'C:\\Users\\mradwin\\ut-gee-ugs-bsf-dev-53dcc5d729e0.json'
    
    if os.path.exists(local_key_path):
        # The older helper function 'ee.ServiceAccountCredentials' automatically handles scopes
        # so we don't need to manually add them here.
        credentials = ee.ServiceAccountCredentials(
            'localpythonscripts@ut-gee-ugs-bsf-dev.iam.gserviceaccount.com', 
            local_key_path
        )
        ee.Initialize(credentials=credentials)
    else:
        st.error("🚨 Authentication Error")
        st.code(f"Detailed Error: {e}")
        st.stop()

# ---------------------------------------------------------
# 2. Helper Functions (Cached for Performance)
# ---------------------------------------------------------
@st.cache_data
def get_bands_from_image(_image: ee.Image, cache_key: str):
    """
    Extracts band names from an ee.Image. 
    The cache_key forces Streamlit to re-run this when the product or date changes.
    """
    return _image.bandNames().getInfo()

# ---------------------------------------------------------
# 3. Product Definitions & Code Injection Areas
# ---------------------------------------------------------
ASSETS = {
    "North Arm Image Collection": 'projects/ut-gee-ugs-bsf-dev/assets/GSLDH_NABRB_Unclassified_Landsat_Col',
    "South Arm Image Collection": 'projects/ut-gee-ugs-bsf-dev/assets/GSLDH_SA_Unclassified_Landsat_Col',
    "North Arm Temporal Anomalies": 'projects/ut-gee-ugs-bsf-dev/assets/GSLDH_NABRB_Unc_Temporal_Anomaly_Landsat_Col',
    "South Arm Temporal Anomalies": 'projects/ut-gee-ugs-bsf-dev/assets/GSLDH_SA_Unc_Temporal_Anomaly_Landsat_Col',
    "Temporal Water Cover Percentage (MNDWI derived)" : 'projects/ut-gee-ugs-bsf-dev/assets/GSL_MNDWI_Temporal_Water_Cover_Percentage',
    "Temporal Water Cover Percentage (NDWI derived)" : 'projects/ut-gee-ugs-bsf-dev/assets/GSL_NDWI_Temporal_Water_Cover_Percentage',
    "Temporal Water Cover Percentage (Shallow Water Isolated)": 'projects/ut-gee-ugs-bsf-dev/assets/GSL_Shallow_Only_Temporal_Water_Cover_Pct_Masked_Halite_and_NDVI',
    "Surface State Instability (Water vs No Water; MNDWI Derived)": 'projects/ut-gee-ugs-bsf-dev/assets/GSL_MNDWI_Water_Cover_Instability_Normalized',
    "Surface State Instability (Water vs No Water; NDWI Derived)": 'projects/ut-gee-ugs-bsf-dev/assets/GSL_NDWI_Water_Cover_Instability_Normalized'

}

STATIC_ASSETS = {
    "Temporal Water Cover Percentage (MNDWI derived)" : 'projects/ut-gee-ugs-bsf-dev/assets/GSL_MNDWI_Temporal_Water_Cover_Percentage',
    "Temporal Water Cover Percentage (NDWI derived)" : 'projects/ut-gee-ugs-bsf-dev/assets/GSL_NDWI_Temporal_Water_Cover_Percentage',
    "Temporal Water Cover Percentage (Shallow Water Isolated)": 'projects/ut-gee-ugs-bsf-dev/assets/GSL_Shallow_Only_Temporal_Water_Cover_Pct_Masked_Halite_and_NDVI',
    "Surface State Instability (Water vs No Water; MNDWI Derived)": 'projects/ut-gee-ugs-bsf-dev/assets/GSL_MNDWI_Water_Cover_Instability_Normalized',
    "Surface State Instability (Water vs No Water; NDWI Derived)": 'projects/ut-gee-ugs-bsf-dev/assets/GSL_NDWI_Water_Cover_Instability_Normalized'

}

# Map anomaly products to their corresponding primary product for RGB retrieval
PRIMARY_RGB_MATCH = {
    "North Arm Temporal Anomalies": "North Arm Image Collection",
    "South Arm Temporal Anomalies": "South Arm Image Collection"
}

NO_PRIMARY_RGB_MATCH = {
    "Temporal Water Cover Percentage (MNDWI derived)" : 'projects/ut-gee-ugs-bsf-dev/assets/GSL_MNDWI_Temporal_Water_Cover_Percentage',
    "Temporal Water Cover Percentage (NDWI derived)" : 'projects/ut-gee-ugs-bsf-dev/assets/GSL_NDWI_Temporal_Water_Cover_Percentage',
    "Temporal Water Cover Percentage (Shallow Water Isolated)": 'projects/ut-gee-ugs-bsf-dev/assets/GSL_Shallow_Only_Temporal_Water_Cover_Pct_Masked_Halite_and_NDVI',
    "Surface State Instability (Water vs No Water; MNDWI Derived)": 'projects/ut-gee-ugs-bsf-dev/assets/GSL_MNDWI_Water_Cover_Instability_Normalized',
    "Surface State Instability (Water vs No Water; NDWI Derived)": 'projects/ut-gee-ugs-bsf-dev/assets/GSL_NDWI_Water_Cover_Instability_Normalized'
}

PERRY_SURVEY_ASSETS = {
    "Hotspot Polygons" : "projects/ut-gee-ugs-bsf-dev/assets/GSLDH_Buffered_Hotspot_Points",
    "Hotspot Survey Points": "projects/ut-gee-ugs-bsf-dev/assets/GSLDH_Filtered_Dust_Hotspot_Points"
}

lake_mask_polygon = ee.Geometry.Polygon(coords=[[[-112.799206, 41.222568], [-112.802124, 41.225021], [-112.810707, 41.227087], [-112.817917, 41.23522], [-112.819118, 41.242062], [-112.816372, 41.258065], [-112.82135, 41.270324], [-112.827873, 41.277032], [-112.831993, 41.281935], [-112.83062, 41.288126], [-112.837486, 41.292254], [-112.841263, 41.297671], [-112.838516, 41.309019], [-112.836456, 41.318302], [-112.834053, 41.3281], [-112.83577, 41.336092], [-112.843323, 41.34666], [-112.852592, 41.352072], [-112.861862, 41.359803], [-112.870445, 41.359288], [-112.880058, 41.363153], [-112.892418, 41.378354], [-112.899971, 41.399475], [-112.907867, 41.403596], [-112.917824, 41.407973], [-112.920914, 41.416728], [-112.922287, 41.426768], [-112.92675, 41.432431], [-112.934647, 41.442212], [-112.936707, 41.449675], [-112.93499, 41.45971], [-112.934303, 41.475917], [-112.936363, 41.48672], [-112.93911, 41.499321], [-112.93808, 41.506006], [-112.9319, 41.51449], [-112.928123, 41.522459], [-112.92881, 41.529399], [-112.914391, 41.537366], [-112.907181, 41.546103], [-112.901344, 41.556123], [-112.895851, 41.564858], [-112.894478, 41.571536], [-112.895508, 41.581552], [-112.895164, 41.596702], [-112.890701, 41.603891], [-112.880745, 41.612876], [-112.873878, 41.622885], [-112.867012, 41.630328], [-112.848816, 41.63546], [-112.842293, 41.635203], [-112.83577, 41.633407], [-112.827187, 41.630584], [-112.817917, 41.628275], [-112.816544, 41.622372], [-112.817917, 41.611079], [-112.812767, 41.602351], [-112.811909, 41.595675], [-112.811737, 41.587844], [-112.812424, 41.581296], [-112.81414, 41.573591], [-112.815857, 41.565885], [-112.816887, 41.557536], [-112.819805, 41.551113], [-112.818432, 41.544047], [-112.816372, 41.540321], [-112.813625, 41.536724], [-112.809162, 41.533254], [-112.804184, 41.529399], [-112.793369, 41.521688], [-112.788391, 41.516547], [-112.78513, 41.512048], [-112.78307, 41.50652], [-112.781696, 41.502921], [-112.778091, 41.501378], [-112.772083, 41.499964], [-112.76659, 41.499321], [-112.761612, 41.497007], [-112.758007, 41.492635], [-112.748051, 41.482219], [-112.744789, 41.476946], [-112.740841, 41.472959], [-112.740669, 41.468457], [-112.741699, 41.464212], [-112.740498, 41.460353], [-112.735176, 41.458295], [-112.730026, 41.45495], [-112.722988, 41.450961], [-112.718353, 41.447487], [-112.714577, 41.444657], [-112.709427, 41.445171], [-112.700157, 41.446072], [-112.703075, 41.443498], [-112.711315, 41.439895], [-112.71492, 41.436807], [-112.712002, 41.435777], [-112.702732, 41.439123], [-112.696381, 41.442984], [-112.693119, 41.445429], [-112.687111, 41.444013], [-112.683163, 41.441697], [-112.678528, 41.435906], [-112.673893, 41.428184], [-112.672005, 41.422263], [-112.658615, 41.414153], [-112.651749, 41.408488], [-112.644882, 41.405398], [-112.637672, 41.401793], [-112.627716, 41.399475], [-112.617416, 41.39999], [-112.60849, 41.400505], [-112.596474, 41.407201], [-112.588577, 41.409776], [-112.579994, 41.409518], [-112.574501, 41.404883], [-112.571068, 41.39587], [-112.567978, 41.386597], [-112.565231, 41.377324], [-112.560081, 41.366761], [-112.556305, 41.358515], [-112.555962, 41.352072], [-112.549782, 41.347433], [-112.543602, 41.34434], [-112.535706, 41.343309], [-112.528152, 41.341763], [-112.521286, 41.338669], [-112.51442, 41.334029], [-112.50721, 41.330936], [-112.504807, 41.325264], [-112.50721, 41.317013], [-112.511673, 41.309019], [-112.518539, 41.303087], [-112.520943, 41.298057], [-112.523003, 41.293543], [-112.528839, 41.289158], [-112.533646, 41.285159], [-112.532272, 41.280903], [-112.533474, 41.276645], [-112.535534, 41.27084], [-112.538624, 41.265292], [-112.542229, 41.262711], [-112.545662, 41.26013], [-112.549095, 41.25613], [-112.549267, 41.252774], [-112.548752, 41.248386], [-112.547379, 41.24374], [-112.546692, 41.239738], [-112.544804, 41.236253], [-112.543087, 41.233155], [-112.539825, 41.230573], [-112.536907, 41.226829], [-112.532616, 41.224118], [-112.528667, 41.221793], [-112.52429, 41.217468], [-112.523346, 41.214627], [-112.522573, 41.211463], [-112.521629, 41.205587], [-112.519999, 41.199904], [-112.517166, 41.195707], [-112.510128, 41.193769], [-112.498798, 41.189894], [-112.486095, 41.188343], [-112.464809, 41.189119], [-112.448158, 41.196998], [-112.422581, 41.19984], [-112.403011, 41.20746], [-112.383957, 41.208364], [-112.350655, 41.199323], [-112.33881, 41.196094], [-112.323704, 41.189119], [-112.318897, 41.184209], [-112.326965, 41.178266], [-112.339325, 41.184597], [-112.359581, 41.184468], [-112.373486, 41.182788], [-112.388935, 41.185501], [-112.397175, 41.182142], [-112.400951, 41.172194], [-112.396317, 41.166637], [-112.363701, 41.151774], [-112.351685, 41.147379], [-112.337608, 41.142984], [-112.327309, 41.137296], [-112.316666, 41.130832], [-112.306709, 41.126435], [-112.295723, 41.125659], [-112.283878, 41.118159], [-112.27787, 41.11609], [-112.27581, 41.113115], [-112.273407, 41.105484], [-112.27169, 41.093972], [-112.268429, 41.088279], [-112.256413, 41.082198], [-112.254868, 41.077669], [-112.265339, 41.077151], [-112.286282, 41.069775], [-112.28714, 41.076634], [-112.284393, 41.084656], [-112.301044, 41.077669], [-112.306709, 41.074304], [-112.307911, 41.082198], [-112.322674, 41.080775], [-112.333488, 41.074951], [-112.337608, 41.064469], [-112.337265, 41.05502], [-112.337265, 41.045311], [-112.335377, 41.039873], [-112.323532, 41.038837], [-112.310486, 41.043886], [-112.29641, 41.052431], [-112.287998, 41.052042], [-112.285252, 41.049194], [-112.29023, 41.043369], [-112.299671, 41.041944], [-112.309456, 41.039484], [-112.309799, 41.033399], [-112.302933, 41.025499], [-112.289543, 41.017858], [-112.281647, 41.014491], [-112.275467, 41.010605], [-112.266369, 41.007755], [-112.260361, 41.006848], [-112.261562, 41.001148], [-112.258301, 40.998168], [-112.260704, 40.989358], [-112.264824, 40.984304], [-112.268085, 40.97925], [-112.26757, 40.975492], [-112.266541, 40.972252], [-112.270832, 40.966419], [-112.272034, 40.960715], [-112.271347, 40.95553], [-112.268257, 40.952289], [-112.268257, 40.949177], [-112.271004, 40.943731], [-112.269287, 40.938285], [-112.264652, 40.931153], [-112.255898, 40.917404], [-112.246628, 40.91001], [-112.245255, 40.905599], [-112.243195, 40.897944], [-112.243195, 40.891066], [-112.243023, 40.883929], [-112.24268, 40.879127], [-112.240105, 40.874454], [-112.235298, 40.869002], [-112.229805, 40.864069], [-112.21796, 40.855111], [-112.212811, 40.850436], [-112.205772, 40.844463], [-112.199078, 40.83771], [-112.192039, 40.831476], [-112.178822, 40.825761], [-112.174187, 40.822124], [-112.169895, 40.820175], [-112.166119, 40.816537], [-112.161655, 40.813549], [-112.160282, 40.810041], [-112.166977, 40.806273], [-112.173672, 40.797827], [-112.182255, 40.78951], [-112.186031, 40.785221], [-112.18586, 40.790744], [-112.18277, 40.795228], [-112.182083, 40.798542], [-112.188177, 40.799841], [-112.195129, 40.799776], [-112.198048, 40.796203], [-112.198305, 40.78925], [-112.201996, 40.782556], [-112.203712, 40.777552], [-112.201996, 40.773457], [-112.200708, 40.767867], [-112.201481, 40.764616], [-112.200794, 40.759741], [-112.200708, 40.756165], [-112.201996, 40.750508], [-112.204828, 40.746412], [-112.211781, 40.744526], [-112.217617, 40.741535], [-112.221909, 40.742055], [-112.227745, 40.739063], [-112.22929, 40.735421], [-112.239418, 40.735291], [-112.246113, 40.735421], [-112.255039, 40.73386], [-112.263107, 40.729958], [-112.270317, 40.726055], [-112.27787, 40.722543], [-112.281647, 40.717729], [-112.289886, 40.715127], [-112.295895, 40.709272], [-112.294521, 40.705628], [-112.300529, 40.706018], [-112.308254, 40.702895], [-112.312374, 40.701464], [-112.317009, 40.703286], [-112.320442, 40.699381], [-112.323189, 40.695477], [-112.325077, 40.690921], [-112.328854, 40.688969], [-112.33469, 40.689099], [-112.340355, 40.687667], [-112.34705, 40.686886], [-112.352371, 40.685064], [-112.357349, 40.684153], [-112.361641, 40.686756], [-112.364731, 40.691963], [-112.365589, 40.701333], [-112.366791, 40.706539], [-112.366619, 40.712785], [-112.366962, 40.71929], [-112.363873, 40.723584], [-112.362328, 40.729438], [-112.358551, 40.732169], [-112.355289, 40.734121], [-112.345676, 40.734121], [-112.33366, 40.734511], [-112.322845, 40.735031], [-112.315121, 40.735551], [-112.311344, 40.737502], [-112.313061, 40.741144], [-112.316837, 40.743746], [-112.323189, 40.745046], [-112.340183, 40.744396], [-112.357006, 40.744006], [-112.363529, 40.745566], [-112.366791, 40.747647], [-112.360096, 40.749728], [-112.355461, 40.753499], [-112.356148, 40.75818], [-112.358379, 40.762731], [-112.362499, 40.768972], [-112.365932, 40.772742], [-112.366791, 40.775082], [-112.358379, 40.775472], [-112.349796, 40.776642], [-112.344646, 40.777552], [-112.344646, 40.780021], [-112.354431, 40.780281], [-112.363701, 40.783011], [-112.366791, 40.78717], [-112.374001, 40.791459], [-112.37915, 40.795618], [-112.383785, 40.795358], [-112.385159, 40.79016], [-112.389622, 40.792239], [-112.394943, 40.793409], [-112.397518, 40.79055], [-112.401123, 40.79029], [-112.407818, 40.793669], [-112.414684, 40.797957], [-112.418804, 40.800036], [-112.417946, 40.804454], [-112.415543, 40.808352], [-112.413139, 40.813809], [-112.419319, 40.815628], [-112.424641, 40.817577], [-112.430477, 40.821604], [-112.436829, 40.825111], [-112.437687, 40.831866], [-112.437, 40.836152], [-112.441978, 40.848099], [-112.444553, 40.857058], [-112.447815, 40.866276], [-112.454338, 40.878088], [-112.461376, 40.88315], [-112.464981, 40.890677], [-112.469788, 40.898852], [-112.475281, 40.908453], [-112.480087, 40.915848], [-112.476482, 40.920388], [-112.478886, 40.924538], [-112.486782, 40.92791], [-112.494335, 40.931153], [-112.502232, 40.935173], [-112.508926, 40.935821], [-112.517166, 40.936081], [-112.521973, 40.939712], [-112.525234, 40.947621], [-112.527809, 40.957215], [-112.531071, 40.967974], [-112.532101, 40.973936], [-112.533474, 40.981972], [-112.534676, 40.987673], [-112.529011, 40.990783], [-112.521801, 40.995059], [-112.523861, 41.000889], [-112.529182, 41.003869], [-112.535877, 41.008403], [-112.540855, 41.01203], [-112.546177, 41.018506], [-112.550468, 41.022262], [-112.553902, 41.026535], [-112.551842, 41.029773], [-112.547722, 41.033658], [-112.539825, 41.036118], [-112.535362, 41.04052], [-112.534676, 41.056185], [-112.535706, 41.066022], [-112.54343, 41.076634], [-112.552872, 41.082845], [-112.563686, 41.088408], [-112.577076, 41.091902], [-112.591324, 41.095524], [-112.596474, 41.096041], [-112.60437, 41.092807], [-112.611923, 41.087762], [-112.622395, 41.079739], [-112.629948, 41.074822], [-112.635956, 41.067057], [-112.639217, 41.059162], [-112.644539, 41.055667], [-112.652264, 41.051525], [-112.659302, 41.040391], [-112.664452, 41.028348], [-112.67149, 41.018765], [-112.67664, 41.010993], [-112.680416, 41.004387], [-112.683334, 40.996095], [-112.685566, 40.987544], [-112.685566, 40.98236], [-112.693291, 40.982879], [-112.701187, 40.986377], [-112.708912, 40.99169], [-112.716293, 40.99778], [-112.719212, 41.000759], [-112.715607, 41.005682], [-112.717838, 41.010605], [-112.722473, 41.014102], [-112.726421, 41.01734], [-112.733803, 41.013972], [-112.737064, 41.016952], [-112.739811, 41.02278], [-112.743416, 41.026665], [-112.744789, 41.032104], [-112.745647, 41.038966], [-112.743931, 41.048677], [-112.745733, 41.056573], [-112.745132, 41.063692], [-112.742729, 41.071199], [-112.747536, 41.084268], [-112.750626, 41.094101], [-112.747192, 41.105743], [-112.747192, 41.121521], [-112.750626, 41.137813], [-112.758865, 41.155393], [-112.764187, 41.166766], [-112.769165, 41.17439], [-112.774143, 41.183434], [-112.780323, 41.19209], [-112.786674, 41.199065], [-112.793884, 41.208622], [-112.797832, 41.214562], [-112.799206, 41.222568]]])
lake_mask_img = ee.Image.constant(1).paint(lake_mask_polygon, 0).rename('lake_mask')
export_geometry = ee.Geometry.Polygon(
        [[[-113.16929521556973, 41.79256891196009],
          [-113.16929521556973, 40.64809349549267],
          [-111.90037431713223, 40.64809349549267],
          [-111.90037431713223, 41.79256891196009]]])

### Shapefiles ###
GSL = ee.FeatureCollection("projects/ut-gee-ugs-bsf-dev/assets/GSL_Shapefiles/GSL_Full_Shape_No_Impoundments")
NA = ee.FeatureCollection("projects/ut-gee-ugs-bsf-dev/assets/GSL_Shapefiles/GSL_NA_Shapefile_No_Evap_Ponds")
SA = ee.FeatureCollection("projects/ut-gee-ugs-bsf-dev/assets/GSL_Shapefiles/GSL_SA_Shapefile_No_Impoundments")
BRB = ee.FeatureCollection("projects/ut-gee-ugs-bsf-dev/assets/GSL_Shapefiles/GSL_BRB_Shape_No_Impoundments")
NA_BRB = NA.merge(BRB)

def _compute_otsu_threshold_vectorized(histogram):
    """
    Calculates Otsu's threshold using ultra-fast linear algebra.
    Replaces slow server-side mapping with a single-pass matrix multiplication
    to calculate cumulative weights and means instantly.
    """
    histogram_dict = ee.Dictionary(histogram)
    
    # Extract 1D arrays, with fallbacks for fully masked/empty images
    counts_1d = ee.Array(histogram_dict.get('histogram', [0]))
    means_1d = ee.Array(histogram_dict.get('bucketMeans', [0]))
    
    # Get total number of buckets (N)
    N = counts_1d.length().get([0])
    
    # Reshape arrays to 2D column vectors (N x 1) for matrix operations
    counts_2d = counts_1d.reshape([-1, 1])
    means_2d = means_1d.reshape([-1, 1])
    
    # Calculate Total Pixels safely
    total = counts_2d.reduce(ee.Reducer.sum(), [0]).get([0, 0])
    safe_total = ee.Algorithms.If(total.eq(0), 1, total)
    
    # Probability (P) and Probability-weighted Mean (M) per bucket
    P = counts_2d.divide(safe_total)
    M = P.multiply(means_2d)
    
    # Global Mean
    M_total = M.reduce(ee.Reducer.sum(), [0]).get([0, 0])
    # Broadcast global mean to an N x 1 array for later subtraction
    M_total_arr = ee.Array(ee.List.repeat(M_total, N)).reshape([-1, 1])
    
    # -------------------------------------------------------------------------
    # THE WIZARD TRICK: Create an N x N Lower Triangular Matrix of 1s.
    # When we multiply this matrix by our probability vectors, it computes 
    # the cumulative sum for all buckets in a single server-side operation!
    # -------------------------------------------------------------------------
    indices_list = ee.List.sequence(0, N.subtract(1))
    # Create N x N grid of column indices
    cols_mat = ee.Array(ee.List.repeat(indices_list, N))
    # Create N x N grid of row indices (transpose of cols)
    rows_mat = cols_mat.transpose()
    # 1 where row >= col (Lower Triangular), 0 otherwise
    lower_tri = rows_mat.gte(cols_mat)
    
    # Calculate Cumulative Probabilities (W) and Cumulative Means (U) instantly
    W = lower_tri.matrixMultiply(P)
    U = lower_tri.matrixMultiply(M)
    
    # -------------------------------------------------------------------------
    # Calculate BCSS (Vectorized)
    # Formula: (M_total * W - U)^2 / (W * (1 - W))
    # -------------------------------------------------------------------------
    
    # Denominator: W * (1 - W)
    # Add a tiny epsilon (1e-10) to prevent division by zero errors on empty classes
    ones_arr = ee.Array(ee.List.repeat(1, N)).reshape([-1, 1])
    epsilon = ee.Array(ee.List.repeat(1e-10, N)).reshape([-1, 1])
    W_minus = ones_arr.subtract(W)
    denominator = W.multiply(W_minus).add(epsilon)
    
    # Numerator: (M_total * W - U)^2 
    # Note: ee.Array lacks a .pow() method, so we multiply the diff by itself
    diff = M_total_arr.multiply(W).subtract(U)
    numerator = diff.multiply(diff)
    
    # Final BCSS Array (N x 1)
    bcss = numerator.divide(denominator)
    
    # THE FIX: Project the 2D N x 1 matrix back to a 1D array.
    # argmax() now returns a 1D coordinate list (e.g., [max_index]) 
    # which can be passed directly into means_1d.get()!
    bcss_1d = bcss.project([0])
    
    return means_1d.get(bcss_1d.argmax())


def apply_dynamic_water_mask(image, index_band='mndwi', region=None, scale=500):
    """
    Computes a dynamic Otsu threshold and returns a binary water mask.
    Optimized for exploratory visualization and large-scale rendering.
    """
    if region is None:
        region = image.geometry()
        
    # Scale Optimization: Increased from 300 to 500 to exponentially reduce 
    # the number of pixels sampled, while maintaining the statistical shape 
    # of the bimodal distribution.
    histogram = image.select(index_band).reduceRegion(
        reducer=ee.Reducer.histogram(maxBuckets=128), # 128 buckets is plenty for continuous indices like NDWI
        geometry=region,
        scale=scale,
        maxPixels=1e10,
        bestEffort=True, # Allows GEE to automatically coarsen scale if geometry is too large
        tileScale=4 
    ).get(index_band)
    
    threshold = ee.Number(_compute_otsu_threshold_vectorized(histogram))
    water_mask = image.select(index_band).gte(threshold).rename(index_band)
    
    return water_mask.copyProperties(image, image.propertyNames()).set('otsu_threshold', threshold)

def calculate_temporal_water_cover_percentage(collection, index_band='mndwi'):
    collection_sum = collection.collection.select(index_band).sum()
    collection_count = collection.collection.select(index_band).count()
    percentage = collection_sum.divide(collection_count).multiply(100).rename(f'{index_band}_temporal_water_cover_percentage')
    return percentage

# def calculate_exposure_duration(binary_water_collection, water_band='water_mask'):
#     """
#     Transforms an ImageCollection of binary water masks into an ImageCollection 
#     representing the number of days since a pixel was last classified as water.
#     """
#     # 1. Ensure the collection is strictly chronological
#     sorted_collection = binary_water_collection.sort('system:time_start')
    
#     # 2. Define the starting state (The Accumulator)
#     initial_state = ee.Dictionary({
#         'last_water_timestamp': ee.Image.constant(0).toLong(),
#         'result_list': ee.List([])
#     })
    
#     # 3. The Iteration Function
#     def _track_exposure(image, state):
#         """ Evaluates the current image, updates the memory, and calculates exposure days. """
#         state = ee.Dictionary(state)
#         previous_timestamp_img = ee.Image(state.get('last_water_timestamp'))
#         result_list = ee.List(state.get('result_list'))
        
#         # Get the current image timestamp in milliseconds
#         current_millis = ee.Number(image.get('system:time_start'))
#         current_date_img = ee.Image.constant(current_millis).toLong()
        
#         # Isolate the binary water mask (1 = water, 0 = land)
#         water_mask = image.select(water_band)
        
#         # ---------------------------------------------------------------------
#         # THE WIZARD TRICK: Global Unmasking
#         # unmask(0) converts clouds AND off-swath areas to 0. 
#         # This allows our 'memory' image to persist globally, calculating the 
#         # exposure age everywhere, even underneath today's clouds and outside 
#         # today's orbital path.
#         # ---------------------------------------------------------------------
#         safe_water_mask = water_mask.unmask(0)
        
#         # Update the timestamp using the globally safe data
#         updated_timestamp_img = previous_timestamp_img.where(safe_water_mask.eq(1), current_date_img)
        
#         # Calculate the days since last inundation
#         millis_since_water = current_date_img.subtract(updated_timestamp_img)
#         days_since_water = millis_since_water.divide(1000 * 60 * 60 * 24).toFloat().rename('days_exposed')
        
#         # ---------------------------------------------------------------------
#         # THE FIX: Apply ONLY the historical boundary mask.
#         # We drop 'current_cloud_mask' entirely. This ensures the output is a 
#         # continuous wall-to-wall map of the lakebed, unaffected by today's clouds.
#         # ---------------------------------------------------------------------
#         valid_history_mask = updated_timestamp_img.gt(0)
#         days_since_water = days_since_water.updateMask(valid_history_mask)
        
#         # Carry over original image metadata
#         days_since_water = days_since_water.copyProperties(image, image.propertyNames())
        
#         return ee.Dictionary({
#             'last_water_timestamp': updated_timestamp_img,
#             'result_list': result_list.add(days_since_water)
#         })

#     # 4. Execute the forward iteration across the collection
#     final_state = ee.Dictionary(sorted_collection.iterate(_track_exposure, initial_state))
    
#     # 5. Extract the accumulated list of result images and cast back to a Collection
#     exposure_collection = ee.ImageCollection.fromImages(ee.List(final_state.get('result_list')))
    
#     return exposure_collection

def calculate_exposure_duration(binary_water_collection, water_band='water_mask'):
    """
    Transforms an ImageCollection of binary water masks into an ImageCollection 
    representing the continuous "Days of No Detected Water" for every pixel.
    
    Args:
        binary_water_collection (ee.ImageCollection): Collection where 1 = water, 0 = non-water.
        water_band (str): The name of the binary mask band.
        
    Returns:
        ee.ImageCollection: A collection where pixel values represent accumulated dry days.
    """
    
    # 1. Ensure the collection is strictly chronological
    sorted_collection = binary_water_collection.sort('system:time_start')
    
    # 2. THE WIZARD TRICK: Initialize with the First Image's Timestamp
    # Instead of 0, we grab the start of the time series. Places that never
    # flood will naturally accumulate the total number of days since this exact moment.
    start_time_millis = ee.Number(sorted_collection.first().get('system:time_start'))
    initial_timestamp_img = ee.Image.constant(start_time_millis).toLong()
    
    # Define the starting state
    initial_state = ee.Dictionary({
        'last_water_timestamp': initial_timestamp_img,
        'result_list': ee.List([])
    })
    
    # 3. The Iteration Function
    def _track_exposure(image, state):
        state = ee.Dictionary(state)
        previous_timestamp_img = ee.Image(state.get('last_water_timestamp'))
        result_list = ee.List(state.get('result_list'))
        
        # Get current image time
        current_millis = ee.Number(image.get('system:time_start'))
        current_date_img = ee.Image.constant(current_millis).toLong()
        
        water_mask = image.select(water_band)
        
        # Unmask to global extent so off-swath and cloudy pixels don't erase history
        safe_water_mask = water_mask.unmask(value=0, sameFootprint=False)
        
        # Update the timestamp: if water is detected today, update to today. Otherwise, keep history.
        updated_timestamp_img = previous_timestamp_img.where(safe_water_mask.eq(1), current_date_img)
        
        # Calculate days of no detected water
        millis_since_water = current_date_img.subtract(updated_timestamp_img)
        days_no_water = millis_since_water.divide(1000 * 60 * 60 * 24).toFloat().rename('days_exposed')
        
        # We REMOVED all masking here! This ensures a solid, continuous wall-to-wall map.
        
        # Carry over original image metadata (crucial for time series plotting)
        days_no_water = days_no_water.copyProperties(image, image.propertyNames())
        
        return ee.Dictionary({
            'last_water_timestamp': updated_timestamp_img,
            'result_list': result_list.add(days_no_water)
        })

    # 4. Execute the forward iteration across the collection
    final_state = ee.Dictionary(sorted_collection.iterate(_track_exposure, initial_state))
    
    # 5. Extract results
    return ee.ImageCollection.fromImages(ee.List(final_state.get('result_list')))

# ---------------------------------------------------------
# 4. Sidebar User Interface
# ---------------------------------------------------------
st.sidebar.header("Data Selection")

product_type = st.sidebar.radio(
    "Select Product Category", 
    ["GEE Asset Collections", "Days Since Last Water"]
)

is_collection = False
selected_image_ee = None 
rgb_image_ee = None # Specific variable to hold the RGB base layer
selected_date = None

if product_type == "GEE Asset Collections":
    
    product_name = st.sidebar.selectbox("Choose Asset:", list(ASSETS.keys()))
    if product_name in STATIC_ASSETS:
        is_collection = False
    else:
        is_collection = True
    asset_path = ASSETS[product_name]
    
    if is_collection is True:
        # Load primary chosen asset
        radgee_col = LandsatCollection(collection=ee.ImageCollection(asset_path))
        dates = radgee_col.dates
        date_to_index = {date: i for i, date in enumerate(dates)}
        
        selected_date = st.sidebar.selectbox(
            "Choose Date:", 
            options=list(reversed(dates)),
            index=0 
        )
        target_index = date_to_index[selected_date]
        selected_image_ee = radgee_col.image_grab(target_index)
        available_bands = get_bands_from_image(selected_image_ee, f"{product_name}_{selected_date}")
        
    else:
        radgee_col = ee.Image(asset_path)
        selected_image_ee = radgee_col
        available_bands = get_bands_from_image(selected_image_ee, f"{product_name}")
    # Pass a cache key so bands re-query when the product/date changes
    
    # Resolve RGB Image for Anomaly Collections
    if product_name in PRIMARY_RGB_MATCH:
        primary_name = PRIMARY_RGB_MATCH[product_name]
        primary_path = ASSETS[primary_name]
        primary_col = LandsatCollection(collection=ee.ImageCollection(primary_path))
        
        if selected_date in primary_col.dates:
            primary_index = primary_col.dates.index(selected_date)
            rgb_image_ee = primary_col.image_grab(primary_index)
        else:
            st.sidebar.warning("RGB base layer not available for this specific date.")
            rgb_image_ee = None

    elif product_name in NO_PRIMARY_RGB_MATCH:
        rgb_image_ee = None

    else:
        rgb_image_ee = selected_image_ee

else:
    product_name = st.sidebar.selectbox(
        "Choose Product:", 
        ["NABRB Days Since Last Water (NDWI)", "NABRB Days Since Last Water (MNDWI)", "SA Days Since Last Water (NDWI)", "SA Days Since Last Water (MNDWI)"]
    )
    
    if product_name == "NABRB Days Since Last Water (NDWI)":
        is_collection = True
        NABRB_asset = ee.ImageCollection('projects/ut-gee-ugs-bsf-dev/assets/GSLDH_NABRB_Unclassified_Landsat_Col')
        NABRB_collection = LandsatCollection(collection=NABRB_asset)
        NA_dates = NABRB_collection.dates
        projection = NABRB_collection.image_grab(-1).projection()
        NA_mndwi = LandsatCollection(collection=NABRB_collection.collection.select('mndwi').map(lambda img: apply_dynamic_water_mask(img, index_band='mndwi'))).mask_out_polygon(lake_mask_polygon)
        NA_ndwi = LandsatCollection(collection=NABRB_collection.collection.select('ndwi').map(lambda img: apply_dynamic_water_mask(img, index_band='ndwi'))).mask_out_polygon(lake_mask_polygon)
        NA_water_timing_mndwi_col = LandsatCollection(collection=calculate_exposure_duration(NA_mndwi.collection, water_band='mndwi')).mask_to_polygon(NA_BRB).mask_out_polygon(lake_mask_polygon)
        NA_water_timing_ndwi_col = LandsatCollection(collection=calculate_exposure_duration(NA_ndwi.collection, water_band='ndwi')).mask_to_polygon(NA_BRB).mask_out_polygon(lake_mask_polygon)

        radgee_col = NA_water_timing_ndwi_col
        
        dates = radgee_col.dates
        date_to_index = {date: i for i, date in enumerate(dates)}
        
        selected_date = st.sidebar.selectbox("Choose Date:", options=list(reversed(dates)), index=0)
        target_index = date_to_index[selected_date]
        selected_image_ee = radgee_col.image_grab(target_index)
        available_bands = get_bands_from_image(selected_image_ee, f"{product_name}_{selected_date}")
        rgb_image_ee = NABRB_collection.image_grab(target_index).select(['SR_B4', 'SR_B3', 'SR_B2'])
        
    elif product_name == "NABRB Days Since Last Water (MNDWI)":
        is_collection = True
        NABRB_asset = ee.ImageCollection('projects/ut-gee-ugs-bsf-dev/assets/GSLDH_NABRB_Unclassified_Landsat_Col')
        NABRB_collection = LandsatCollection(collection=NABRB_asset)
        NA_dates = NABRB_collection.dates
        projection = NABRB_collection.image_grab(-1).projection()
        NA_mndwi = LandsatCollection(collection=NABRB_collection.collection.select('mndwi').map(lambda img: apply_dynamic_water_mask(img, index_band='mndwi'))).mask_out_polygon(lake_mask_polygon)
        NA_ndwi = LandsatCollection(collection=NABRB_collection.collection.select('ndwi').map(lambda img: apply_dynamic_water_mask(img, index_band='ndwi'))).mask_out_polygon(lake_mask_polygon)
        NA_water_timing_mndwi_col = LandsatCollection(collection=calculate_exposure_duration(NA_mndwi.collection, water_band='mndwi')).mask_to_polygon(NA_BRB).mask_out_polygon(lake_mask_polygon)
        NA_water_timing_ndwi_col = LandsatCollection(collection=calculate_exposure_duration(NA_ndwi.collection, water_band='ndwi')).mask_to_polygon(NA_BRB).mask_out_polygon(lake_mask_polygon)

        radgee_col = NA_water_timing_mndwi_col
        
        dates = radgee_col.dates
        date_to_index = {date: i for i, date in enumerate(dates)}
        
        selected_date = st.sidebar.selectbox("Choose Date:", options=list(reversed(dates)), index=0)
        target_index = date_to_index[selected_date]
        selected_image_ee = radgee_col.image_grab(target_index)
        available_bands = get_bands_from_image(selected_image_ee, f"{product_name}_{selected_date}")
        rgb_image_ee = NABRB_collection.image_grab(target_index).select(['SR_B4', 'SR_B3', 'SR_B2'])

    elif product_name == "SA Days Since Last Water (NDWI)":
        is_collection = True
        SA_asset = ee.ImageCollection('projects/ut-gee-ugs-bsf-dev/assets/GSLDH_SA_Unclassified_Landsat_Col')
        SA_collection = LandsatCollection(collection=SA_asset)
        SA_dates = SA_collection.dates
        projection = SA_collection.image_grab(-1).projection()
        SA_mndwi = LandsatCollection(collection=SA_collection.collection.select('mndwi').map(lambda img: apply_dynamic_water_mask(img, index_band='mndwi'))).mask_out_polygon(lake_mask_polygon)
        SA_ndwi = LandsatCollection(collection=SA_collection.collection.select('ndwi').map(lambda img: apply_dynamic_water_mask(img, index_band='ndwi'))).mask_out_polygon(lake_mask_polygon)
        SA_water_timing_mndwi_col = LandsatCollection(collection=calculate_exposure_duration(SA_mndwi.collection, water_band='mndwi')).mask_to_polygon(SA).mask_out_polygon(lake_mask_polygon)
        SA_water_timing_ndwi_col = LandsatCollection(collection=calculate_exposure_duration(SA_ndwi.collection, water_band='ndwi')).mask_to_polygon(SA).mask_out_polygon(lake_mask_polygon)

        radgee_col = SA_water_timing_ndwi_col
        
        dates = radgee_col.dates
        date_to_index = {date: i for i, date in enumerate(dates)}
        
        selected_date = st.sidebar.selectbox("Choose Date:", options=list(reversed(dates)), index=0)
        target_index = date_to_index[selected_date]
        # selected_image_ee = radgee_col.image_grab(target_index)
        selected_image_ee = radgee_col.image_pick(str(selected_date))
        available_bands = get_bands_from_image(selected_image_ee, f"{product_name}_{selected_date}")
        # rgb_image_ee = SA_collection.image_grab(target_index).select(['SR_B4', 'SR_B3', 'SR_B2'])
        rgb_image_ee = SA_collection.image_pick(str(selected_date)).select(['SR_B4', 'SR_B3', 'SR_B2'])

    elif product_name == "SA Days Since Last Water (MNDWI)":
        is_collection = True
        SA_asset = ee.ImageCollection('projects/ut-gee-ugs-bsf-dev/assets/GSLDH_SA_Unclassified_Landsat_Col')
        SA_collection = LandsatCollection(collection=SA_asset)
        SA_dates = SA_collection.dates
        projection = SA_collection.image_grab(-1).projection()
        SA_mndwi = LandsatCollection(collection=SA_collection.collection.select('mndwi').map(lambda img: apply_dynamic_water_mask(img, index_band='mndwi'))).mask_out_polygon(lake_mask_polygon)
        SA_ndwi = LandsatCollection(collection=SA_collection.collection.select('ndwi').map(lambda img: apply_dynamic_water_mask(img, index_band='ndwi'))).mask_out_polygon(lake_mask_polygon)
        SA_water_timing_mndwi_col = LandsatCollection(collection=calculate_exposure_duration(SA_mndwi.collection, water_band='mndwi')).mask_to_polygon(SA).mask_out_polygon(lake_mask_polygon)
        SA_water_timing_ndwi_col = LandsatCollection(collection=calculate_exposure_duration(SA_ndwi.collection, water_band='ndwi')).mask_to_polygon(SA).mask_out_polygon(lake_mask_polygon)

        radgee_col = SA_water_timing_mndwi_col
        
        dates = radgee_col.dates
        date_to_index = {date: i for i, date in enumerate(dates)}
        
        selected_date = st.sidebar.selectbox("Choose Date:", options=list(reversed(dates)), index=0)
        target_index = date_to_index[selected_date]
        # selected_image_ee = radgee_col.image_grab(target_index)
        selected_image_ee = radgee_col.image_pick(str(selected_date))
        available_bands = get_bands_from_image(selected_image_ee, f"{product_name}_{selected_date}")
        # rgb_image_ee = SA_collection.image_grab(target_index).select(['SR_B4', 'SR_B3', 'SR_B2'])
        rgb_image_ee = SA_collection.image_pick(str(selected_date)).select(['SR_B4', 'SR_B3', 'SR_B2'])

perry_survey_vis_options = st.sidebar.selectbox("Perry Survey Options", options=["None", "Hotspot Polygons", "Hotspot Points"], index=0)
        

st.sidebar.header("Visualization Options")

# Band Selection
if product_type == "GEE Asset Collections":
    if product_name in STATIC_ASSETS:
        if len(available_bands) == 1:
            viz_band = available_bands[0]
        else:
            viz_band = st.sidebar.selectbox("Select Band to Visualize:", available_bands, index=0)
    elif "Anomal" in product_name:
        viz_band = st.sidebar.selectbox("Select Band to Visualize:", available_bands, index=0)
        
    else:
        viz_band = st.sidebar.selectbox("Select Band to Visualize:", available_bands, index=4)
elif product_type == "Days Since Last Water":
    viz_band = st.sidebar.selectbox("Select Band to Visualize:", available_bands, index=0)

# --- NEW LOGIC: Dynamic Defaults based on Product Type ---
is_anomaly = "anomal" in product_name.lower() or "anomal" in viz_band.lower()
is_days_since = "days since last water" in product_name.lower()
is_percentage = "percentage" in product_name.lower()
is_instability = "instability" in product_name.lower()

palette_options = ["inferno", "magma", "viridis", "cividis", "reds", "blues", "rdbu", "jet"]

if is_anomaly:
    default_min = -0.2
    default_max = 0.2
    default_palette_index = palette_options.index("rdbu")
elif is_days_since:
    default_min = 0.0
    default_max = 100.0  # Max stretch defaults to 100
    default_palette_index = 0 
elif is_percentage:
    default_min = 0.0
    default_max = 100.0
    default_palette_index = palette_options.index("jet")
elif is_instability:
    default_min = 0.0
    default_max = 0.6
    default_palette_index = palette_options.index("inferno")
else:
    default_min = 0.0
    default_max = 1.0
    default_palette_index = 0
# --------------------------------------------------------

# Palette, Min, Max
col1, col2 = st.sidebar.columns(2)
viz_min = col1.number_input("Min", value=default_min)
viz_max = col2.number_input("Max", value=default_max)

palette_choice = st.sidebar.selectbox(
    "Color Palette:", 
    palette_options,
    index=default_palette_index
)

# ---------------------------------------------------------
# 5. Map Rendering
# ---------------------------------------------------------
# ---------------------------------------------------------
# 5. Map Rendering
# ---------------------------------------------------------
# if gee_ready and selected_image_ee:
if selected_image_ee:
    st.subheader(f"Viewing: {product_name}, Date: {selected_date if selected_date else 'N/A'}, Band: {viz_band}")
    if 'Days Since' in product_name:
        st.markdown("Please allow up to a minute or two for the 'Days Since Last Water' products to render, as they are calculated on-the-fly.")
    elif 'Instability' in product_name:
        st.markdown("This product ranges from 0 to 1, where higher values indicate greater instability in water presence over time. Areas with values close to 0 have been consistently stable (either always water or always land), while values closer to 1 indicate areas that frequently switch between water and land across the time series. Masked pixels have a value of 0, indicating no detected instability (either due to consistent land/water or lack of data).")
    elif "Temporal Anomal" in product_name:
        st.markdown("Temporal anomalies are calculated by comparing the selected date's value to the monthly climatology for that specific calendar month across the entire time series. Positive anomalies indicate higher-than-average values for that month, while negative anomalies indicate lower-than-average values. This helps identify unusual conditions relative to typical seasonal patterns.")
    # Initialize Map using values from session_state
    if any(x in product_name for x in ["North Arm", "NA"]):
        Map = geemap.Map(center=[41.5, -112.5], zoom=10)
    elif any(x in product_name for x in ["South Arm", "SA"]):
        Map = geemap.Map(center=[40.95, -112.5], zoom=10)
    else:
        Map = geemap.Map(center=[41.15, -112.5], zoom=9)
    
    # ADD RGB BASE LAYER
    if is_collection and rgb_image_ee:
        try:
            Map.addLayer(
                rgb_image_ee, 
                vis_params={'bands': ['SR_B4', 'SR_B3', 'SR_B2'], 'min': 0, 'max': 0.6, 'gamma': 1.5}, 
                name='RGB True Color (Base)',
                shown=True
            )
        except Exception as e:
            st.warning("Could not render RGB base layer. Ensure SR bands exist on this image.")
    
    # ADD USER SELECTED PRODUCT LAYER
    vis_params_custom = {
        'bands': [viz_band],
        'min': viz_min,
        'max': viz_max,
        'palette': get_palette(palette_choice),
        'opacity': 1
    }
    Map.addLayer(
        selected_image_ee, 
        vis_params=vis_params_custom, 
        name=f'{viz_band} Viz'
    )

    Map.add_colorbar(
        vis_params_custom, 
        label=f'{viz_band} Value', 
        orientation='horizontal'
    )

    if perry_survey_vis_options == "Hotspot Polygons":
        Map.addLayer(ee.FeatureCollection(PERRY_SURVEY_ASSETS["Hotspot Polygons"]),
                     vis_params={'opacity': 0.6},
            name="Perry Hotspot Polygons")
    elif perry_survey_vis_options == "Hotspot Points":
        Map.addLayer(ee.FeatureCollection(PERRY_SURVEY_ASSETS["Hotspot Points"]),
                     vis_params={'opacity': 0.6},
            name="Perry Hotspot Points")
    elif perry_survey_vis_options == "None":
        pass
    
    Map.to_streamlit(height=600)

    # ---------------------------------------------------------
    # Render map using st_folium to capture bidirectional state
    # ---------------------------------------------------------
    # We specify returned_objects to optimize performance so it only sends back what we need
    # map_output = st_folium(Map, width="100%", height=600, returned_objects=["center", "zoom"])
    
    # # Update session state with the last known map extent
    # if map_output and map_output.get("center") is not None:
    #     st.session_state.map_center = [map_output["center"]["lat"], map_output["center"]["lng"]]
    #     st.session_state.map_zoom = map_output["zoom"]