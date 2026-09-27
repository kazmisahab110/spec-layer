// ============================================================
// SPECLAYER — TYPESCRIPT API CONTRACT
// ============================================================
//
// IMPORTANT:
//
// This file is NOT loaded by index.html yet.
//
// Browsers execute script.js directly.
//
// Later, when we introduce TypeScript tooling / Vite,
// this file can replace the plain JavaScript implementation.
//
// For the current prototype:
//
// index.html
//      ↓
// script.js
//      ↓
// FastAPI
//
// ============================================================


// ============================================================
// 1. BACKEND CONFIGURATION
// ============================================================

const API_BASE_URL_TS: string =
    "http://127.0.0.1:8000";

const ANALYZE_ENDPOINT_TS: string =
    `${API_BASE_URL_TS}/analyze`;


// ============================================================
// 2. DEVICE TYPES
// ============================================================

interface DeviceResult {

    device_type?: string | null;

    manufacturer?: string | null;

    model?: string | null;

    uncertainties?: string[];

}


// ============================================================
// 3. SOURCE TYPES
// ============================================================

interface SourceResult {

    source_id?: string;

    title?: string;

    url?: string;

    relevance_score?: number;

}


// ============================================================
// 4. MEDIA TYPES
// ============================================================

interface ImageReference {

    image_url?: string | null;

    thumbnail_url?: string | null;

    source?: string | null;

}


interface Model3DReference {

    viewer_url?: string | null;

    model_url?: string | null;

    thumbnail_url?: string | null;

    source?: string | null;

    name?: string | null;

}


// ============================================================
// 5. COMPONENT TYPES
// ============================================================

interface ComponentMedia {

    image?: ImageReference | null;

    model_3d?: Model3DReference | null;

}


interface ComponentResult {

    name?: string;

    scope?: string;

    function?: string;

    evidence_level?: string;

    source_ids?: string[];

    media?: ComponentMedia;

}


// ============================================================
// 6. RELATIONSHIP TYPES
// ============================================================

interface ComponentRelationship {

    source?: string;

    target?: string;

    relationship?: string;

}


// ============================================================
// 7. ANALYSIS TYPE
// ============================================================
//
// The backend is still evolving, so most fields remain
// optional for now.
//
// Once the backend API contract is completely stable,
// these can become stricter.
// ============================================================

interface AnalysisResult {

    components?: ComponentResult[];

    internal_components?: ComponentResult[];

    external_components?: ComponentResult[];

    relationships?: ComponentRelationship[];

    limitations?: string[];

}


// ============================================================
// 8. COMPLETE /analyze RESPONSE
// ============================================================

interface AnalyzeResponse {

    device: DeviceResult;

    sources: SourceResult[];

    analysis: AnalysisResult;

}


// ============================================================
// 9. TYPED BACKEND REQUEST
// ============================================================
//
// This is the TypeScript equivalent of the fetch request
// currently used by script.js.
//
// We are NOT calling this function from the webpage yet.
// ============================================================

async function analyzeEquipmentTyped(
    file: File
): Promise<AnalyzeResponse> {

    const formData: FormData =
        new FormData();


    formData.append(
        "file",
        file
    );


    const response: Response =
        await fetch(
            ANALYZE_ENDPOINT_TS,
            {
                method: "POST",

                body: formData
            }
        );


    const data: unknown =
        await response.json();


    if (!response.ok) {

        let message: string =
            "Backend analysis failed.";


        if (
            typeof data === "object" &&
            data !== null &&
            "detail" in data
        ) {

            const detail =
                (data as { detail?: unknown })
                    .detail;


            if (
                typeof detail === "string"
            ) {

                message = detail;

            }

        }


        throw new Error(
            message
        );

    }


    return data as AnalyzeResponse;

}


// ============================================================
// 10. FUTURE USE
// ============================================================
//
// Later:
//
// const result: AnalyzeResponse =
//     await analyzeEquipmentTyped(file);
//
// result.device.manufacturer
// result.device.model
// result.sources
// result.analysis.components
//
// TypeScript will then warn us if frontend code tries to use
// backend data incorrectly.
//
// ============================================================