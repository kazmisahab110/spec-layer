// ============================================================
// SPECLAYER — SIMPLE FRONTEND/BACKEND CONNECTION TEST
// ============================================================
//
// Current purpose:
//
// 1. Let the user choose an image.
// 2. Preview the image.
// 3. Send the image to FastAPI.
// 4. Wait for /analyze.
// 5. Confirm that JSON comes back.
// 6. Show basic device information.
//
// Nothing complicated yet.
// ============================================================


// ============================================================
// 1. BACKEND CONFIGURATION
// ============================================================

// Your FastAPI backend.
//
// If Uvicorn is running with:
//
// uvicorn app.main:app --reload
//
// FastAPI normally runs at:
// http://127.0.0.1:8000

const API_BASE_URL = "http://127.0.0.1:8000";

const ANALYZE_ENDPOINT = `${API_BASE_URL}/analyze`;


// ============================================================
// 2. GET HTML ELEMENTS
// ============================================================

const imageInput = document.getElementById("image-input");

const browseButton = document.getElementById("browse-button");

const uploadCard = document.getElementById("upload-card");

const uploadEmpty = document.getElementById("upload-empty");

const uploadPreview = document.getElementById("upload-preview");

const imagePreview = document.getElementById("image-preview");

const selectedFileName = document.getElementById(
    "selected-file-name"
);

const removeImageButton = document.getElementById(
    "remove-image-button"
);

const analyzeButton = document.getElementById(
    "analyze-button"
);


// Screens

const uploadScreen = document.getElementById(
    "upload-screen"
);

const loadingScreen = document.getElementById(
    "loading-screen"
);

const workspaceScreen = document.getElementById(
    "workspace-screen"
);

const errorScreen = document.getElementById(
    "error-screen"
);


// Loading UI

const loadingTitle = document.getElementById(
    "loading-title"
);

const loadingDescription = document.getElementById(
    "loading-description"
);

const loadingProgressFill = document.getElementById(
    "loading-progress-fill"
);


// Result UI

const deviceName = document.getElementById(
    "device-name"
);

const deviceType = document.getElementById(
    "device-type"
);

const deviceStatus = document.getElementById(
    "device-status"
);

const componentCount = document.getElementById(
    "component-count"
);

const sourceCount = document.getElementById(
    "source-count"
);


// Error UI

const errorMessage = document.getElementById(
    "error-message"
);

const tryAgainButton = document.getElementById(
    "try-again-button"
);

const newAnalysisButton = document.getElementById(
    "new-analysis-button"
);


// Settings

const settingsButton = document.getElementById(
    "settings-button"
);

const settingsDrawer = document.getElementById(
    "settings-drawer"
);

const settingsOverlay = document.getElementById(
    "settings-overlay"
);

const closeSettingsButton = document.getElementById(
    "close-settings-button"
);


// ============================================================
// 3. SIMPLE APPLICATION STATE
// ============================================================

let selectedFile = null;


// ============================================================
// 4. SCREEN HELPER
// ============================================================

function showScreen(screen) {

    uploadScreen.classList.add("hidden");
    loadingScreen.classList.add("hidden");
    workspaceScreen.classList.add("hidden");
    errorScreen.classList.add("hidden");

    screen.classList.remove("hidden");
}


// ============================================================
// 5. OPEN FILE SELECTOR
// ============================================================

browseButton.addEventListener("click", function () {

    imageInput.click();

});


// ============================================================
// 6. HANDLE FILE SELECTION
// ============================================================

imageInput.addEventListener("change", function (event) {

    const file = event.target.files[0];

    if (!file) {
        return;
    }

    selectImage(file);

});


// ============================================================
// 7. SELECT + PREVIEW IMAGE
// ============================================================

function selectImage(file) {

    // Only accept image files.

    if (!file.type.startsWith("image/")) {

        alert("Please select an image file.");

        return;
    }


    selectedFile = file;


    // Show filename.

    selectedFileName.textContent = file.name;


    // Create temporary browser preview URL.

    const previewUrl = URL.createObjectURL(file);

    imagePreview.src = previewUrl;


    // Hide empty upload UI.

    uploadEmpty.classList.add("hidden");


    // Show image preview UI.

    uploadPreview.classList.remove("hidden");


    console.log(
        "[SpecLayer] Selected image:",
        file.name
    );
}


// ============================================================
// 8. REMOVE IMAGE
// ============================================================

removeImageButton.addEventListener(
    "click",
    function () {

        resetImageSelection();

    }
);


function resetImageSelection() {

    selectedFile = null;

    imageInput.value = "";

    imagePreview.src = "";

    selectedFileName.textContent = "";

    uploadPreview.classList.add("hidden");

    uploadEmpty.classList.remove("hidden");

}


// ============================================================
// 9. OPTIONAL DRAG + DROP
// ============================================================

uploadCard.addEventListener(
    "dragover",
    function (event) {

        event.preventDefault();

        uploadCard.classList.add(
            "drag-active"
        );

    }
);


uploadCard.addEventListener(
    "dragleave",
    function () {

        uploadCard.classList.remove(
            "drag-active"
        );

    }
);


uploadCard.addEventListener(
    "drop",
    function (event) {

        event.preventDefault();

        uploadCard.classList.remove(
            "drag-active"
        );


        const file =
            event.dataTransfer.files[0];


        if (!file) {
            return;
        }


        selectImage(file);

    }
);


// ============================================================
// 10. ANALYZE BUTTON
// ============================================================

analyzeButton.addEventListener(
    "click",
    function () {

        analyzeEquipment();

    }
);


// ============================================================
// 11. SEND IMAGE TO FASTAPI
// ============================================================

async function analyzeEquipment() {

    if (!selectedFile) {

        alert(
            "Please select an equipment image first."
        );

        return;
    }


    // ----------------------------------------
    // Show loading screen
    // ----------------------------------------

    showScreen(loadingScreen);

    loadingTitle.textContent =
        "ANALYZING EQUIPMENT";

    loadingDescription.textContent =
        "Sending image to the SpecLayer backend...";

    loadingProgressFill.style.width =
        "30%";


    // ----------------------------------------
    // Create multipart form data
    // ----------------------------------------
    //
    // Your FastAPI endpoint expects:
    //
    // file: UploadFile = File(...)
    //
    // Therefore the field MUST be named "file".
    // ----------------------------------------

    const formData = new FormData();

    formData.append(
        "file",
        selectedFile
    );


    try {

        console.log(
            "[SpecLayer] Sending image to:",
            ANALYZE_ENDPOINT
        );


        loadingProgressFill.style.width =
            "55%";

        loadingDescription.textContent =
            "Waiting for equipment analysis...";


        // ------------------------------------
        // POST request
        // ------------------------------------

        const response = await fetch(
            ANALYZE_ENDPOINT,
            {
                method: "POST",

                body: formData
            }
        );


        console.log(
            "[SpecLayer] HTTP status:",
            response.status
        );


        // ------------------------------------
        // Read JSON response
        // ------------------------------------

        let data;

        try {

            data = await response.json();

        }
        catch {

            throw new Error(
                "Backend returned a response that was not valid JSON."
            );

        }


        // ------------------------------------
        // Handle FastAPI errors
        // ------------------------------------

        if (!response.ok) {

            const backendMessage =
                data?.detail ||
                "Backend analysis failed.";

            throw new Error(
                backendMessage
            );

        }


        // ------------------------------------
        // SUCCESS
        // ------------------------------------

        console.log(
            "[SpecLayer] Backend response:"
        );

        console.log(data);


        loadingProgressFill.style.width =
            "100%";

        loadingTitle.textContent =
            "ANALYSIS COMPLETE";

        loadingDescription.textContent =
            "Backend connection successful.";


        // Small delay so we can visually see
        // that the request completed.

        setTimeout(
            function () {

                displaySimpleResult(data);

            },
            400
        );

    }
    catch (error) {

        console.error(
            "[SpecLayer] Request failed:",
            error
        );


        showError(
            error.message
        );

    }

}


// ============================================================
// 12. DISPLAY SIMPLE RESULT
// ============================================================
//
// IMPORTANT:
//
// We're intentionally NOT building the full UI yet.
//
// We only display:
//
// - manufacturer
// - model
// - device type
// - component count
// - source count
//
// That proves:
//
// Browser -> FastAPI -> AI pipeline -> JSON -> Browser
//
// works.
// ============================================================

function displaySimpleResult(data) {

    const device =
        data.device || {};


    const manufacturer =
        device.manufacturer ||
        "Unknown manufacturer";


    const model =
        device.model ||
        "Unknown model";


    const type =
        device.device_type ||
        "Unknown equipment";


    // ----------------------------------------
    // Device name
    // ----------------------------------------

    if (
        device.manufacturer &&
        device.model
    ) {

        deviceName.textContent =
            `${device.manufacturer} ${device.model}`;

    }
    else if (device.model) {

        deviceName.textContent =
            device.model;

    }
    else if (device.manufacturer) {

        deviceName.textContent =
            device.manufacturer;

    }
    else {

        deviceName.textContent =
            type;

    }


    deviceType.textContent =
        type;


    deviceStatus.textContent =
        "BACKEND CONNECTED";


    // ----------------------------------------
    // Count sources
    // ----------------------------------------

    const sources =
        Array.isArray(data.sources)
            ? data.sources
            : [];


    sourceCount.textContent =
        String(sources.length);


    // ----------------------------------------
    // Count components
    // ----------------------------------------

    const analysis =
        data.analysis || {};


    let components = [];


    // Support a few possible structures while
    // we're still stabilizing the API contract.

    if (
        Array.isArray(
            analysis.components
        )
    ) {

        components =
            analysis.components;

    }
    else if (
        Array.isArray(
            analysis.internal_components
        )
    ) {

        components =
            analysis.internal_components;

    }


    componentCount.textContent =
        String(components.length);


    // ----------------------------------------
    // Show results workspace
    // ----------------------------------------

    showScreen(
        workspaceScreen
    );


    console.log(
        "[SpecLayer] CONNECTION TEST SUCCESS"
    );

    console.log(
        "Manufacturer:",
        manufacturer
    );

    console.log(
        "Model:",
        model
    );

    console.log(
        "Device type:",
        type
    );

    console.log(
        "Sources:",
        sources.length
    );

    console.log(
        "Components:",
        components.length
    );

}


// ============================================================
// 13. ERROR HANDLING
// ============================================================

function showError(message) {

    errorMessage.textContent =
        message ||
        "Unable to communicate with the backend.";

    showScreen(
        errorScreen
    );

}


// ============================================================
// 14. TRY AGAIN
// ============================================================

tryAgainButton.addEventListener(
    "click",
    function () {

        showScreen(
            uploadScreen
        );

    }
);


// ============================================================
// 15. NEW ANALYSIS
// ============================================================

newAnalysisButton.addEventListener(
    "click",
    function () {

        resetImageSelection();

        showScreen(
            uploadScreen
        );

    }
);


// ============================================================
// 16. SETTINGS DRAWER
// ============================================================

function openSettings() {

    settingsDrawer.classList.add(
        "open"
    );

    settingsDrawer.setAttribute(
        "aria-hidden",
        "false"
    );

    settingsOverlay.classList.remove(
        "hidden"
    );

}


function closeSettings() {

    settingsDrawer.classList.remove(
        "open"
    );

    settingsDrawer.setAttribute(
        "aria-hidden",
        "true"
    );

    settingsOverlay.classList.add(
        "hidden"
    );

}


settingsButton.addEventListener(
    "click",
    openSettings
);


closeSettingsButton.addEventListener(
    "click",
    closeSettings
);


settingsOverlay.addEventListener(
    "click",
    closeSettings
);


// ============================================================
// 17. INITIAL STARTUP
// ============================================================

console.log(
    "[SpecLayer] Frontend loaded."
);

console.log(
    "[SpecLayer] Backend:",
    API_BASE_URL
);

console.log(
    "[SpecLayer] Waiting for image."
);