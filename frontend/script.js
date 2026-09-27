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

let currentAnalysis = null;


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

const componentGraph = document.getElementById(
    "component-graph"
);

const componentList = document.getElementById(
    "component-list"
);

const filterButtons = document.querySelectorAll(
    ".filter-button"
);

const sourceCount = document.getElementById(
    "source-count"
);

const componentImageFrame =
    document.getElementById("component-image-frame");

// Inspector UI

const inspectorEmpty = document.getElementById(
    "inspector-empty"
);

const inspectorContent = document.getElementById(
    "inspector-content"
);

const componentScope = document.getElementById(
    "component-scope"
);

const componentName = document.getElementById(
    "component-name"
);

const componentEvidence = document.getElementById(
    "component-evidence"
);

const componentFunction = document.getElementById(
    "component-function"
);

const componentSourceList = document.getElementById(
    "component-source-list"
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
let activeComponentFilter = "all";


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

        currentAnalysis = data;

        // Expose it so we can inspect it in
        // the browser Developer Tools console.
        window.currentAnalysis = data;

        console.log(
            "[SpecLayer] Full analysis stored:",
            currentAnalysis
        );


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

    renderComponentList(components);

    renderComponentGraph(components);


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
// 13. RENDER COMPONENT LIST
// ============================================================

function renderComponentList(components) {

    componentList.innerHTML = "";

    if (!Array.isArray(components)) {
        return;
    }

    if (components.length === 0) {

        const emptyMessage =
            document.createElement("div");

        emptyMessage.className =
            "component-list-empty";

        emptyMessage.textContent =
            "No documented components found.";

        componentList.appendChild(
            emptyMessage
        );

        return;
    }


    components.forEach(function (component) {

        const item =
            document.createElement("button");

        item.type = "button";

        item.className =
            "component-item";

        item.dataset.componentId =
            component.id || "";


        const name =
            document.createElement("span");

        name.className =
            "component-item-name";

        name.textContent =
            component.name ||
            "Unnamed component";


        const scope =
            document.createElement("span");

        scope.className =
            "component-item-scope";

        scope.textContent =
            component.scope ||
            "unknown";


        item.appendChild(name);
        item.appendChild(scope);


        // ------------------------------------
        // Component selection
        // ------------------------------------

        item.addEventListener(
            "click",
            function () {

                selectComponent(
                    component,
                    item
                );

            }
        );


        componentList.appendChild(item);

    });

}

// ============================================================
// RENDER COMPONENT GRAPH
// ============================================================

function renderComponentGraph(components) {

    componentGraph.innerHTML = "";

    if (!Array.isArray(components)) {
        return;
    }


    // ----------------------------------------
    // Empty graph state
    // ----------------------------------------

    if (components.length === 0) {

        const emptyState =
            document.createElement("div");

        emptyState.className =
            "graph-empty-state";

        emptyState.innerHTML = `
            <div class="graph-empty-icon">
                <span class="material-symbols-outlined">
                    account_tree
                </span>
            </div>

            <h3>No documented components</h3>

            <p>
                No component nodes were returned
                for this analysis.
            </p>
        `;

        componentGraph.appendChild(
            emptyState
        );

        return;
    }


    // ----------------------------------------
    // Node layer
    // ----------------------------------------

    const nodeLayer =
        document.createElement("div");

    nodeLayer.className =
        "graph-node-layer";


    const total =
        components.length;


    components.forEach(
        function (component, index) {

            const node =
                document.createElement("button");

            node.type = "button";

            node.className =
                "graph-node";

            node.dataset.componentId =
                component.id || "";

            node.dataset.scope =
                component.scope || "unknown";

            node.title =
                component.name ||
                "Unnamed component";


            // --------------------------------
            // Responsive grid layout
            // --------------------------------

            const columns =
                total <= 4
                    ? 2
                    : total <= 9
                        ? 3
                        : 4;

            const rows =
                Math.ceil(
                    total / columns
                );

            const column =
                index % columns;

            const row =
                Math.floor(
                    index / columns
                );


            const x =
                columns === 1
                    ? 50
                    : 10 +
                    (
                        column /
                        (columns - 1)
                    ) * 80;


            const y =
                rows === 1
                    ? 50
                    : 12 +
                        (
                            row /
                            (rows - 1)
                        ) * 76;

            node.style.left =
                `${x}%`;

            node.style.top =
                `${y}%`;


            // --------------------------------
            // Scope marker
            // --------------------------------

            const marker =
                document.createElement("span");

            marker.className =
                "graph-node-marker";


            // --------------------------------
            // Text
            // --------------------------------

            const copy =
                document.createElement("span");

            copy.className =
                "graph-node-copy";


            const name =
                document.createElement("strong");

            name.textContent =
                component.name ||
                "Unnamed component";


            const scope =
                document.createElement("small");

            scope.textContent =
                (
                    component.scope ||
                    "unknown"
                ).toUpperCase();


            copy.appendChild(name);
            copy.appendChild(scope);

            node.appendChild(marker);
            node.appendChild(copy);


            // --------------------------------
            // Select component from graph
            // --------------------------------

            node.addEventListener(
                "click",
                function () {

                    selectGraphComponent(
                        component,
                        node
                    );

                }
            );


            nodeLayer.appendChild(
                node
            );

        }
    );


    componentGraph.appendChild(
        nodeLayer
    );

}

// ============================================================
// GRAPH COMPONENT SELECTION
// ============================================================

function selectGraphComponent(
    component,
    selectedNode
) {

    // ----------------------------------------
    // Clear previous graph selection
    // ----------------------------------------

    const graphNodes =
        componentGraph.querySelectorAll(
            ".graph-node"
        );

    graphNodes.forEach(function (node) {

        node.classList.remove(
            "active"
        );

    });


    // ----------------------------------------
    // Highlight selected graph node
    // ----------------------------------------

    if (selectedNode) {

        selectedNode.classList.add(
            "active"
        );

    }


    // ----------------------------------------
    // Find matching sidebar component
    // ----------------------------------------

    const sidebarItems =
        componentList.querySelectorAll(
            ".component-item"
        );

    let matchingSidebarItem = null;

    sidebarItems.forEach(function (item) {

        if (
            item.dataset.componentId ===
            component.id
        ) {

            matchingSidebarItem = item;

        }

    });


    // ----------------------------------------
    // Reuse our working Inspector selection
    // ----------------------------------------

    selectComponent(
        component,
        matchingSidebarItem
    );

}

// ============================================================
// GRAPH COMPONENT SELECTION
// ============================================================

function selectGraphComponent(
    component,
    selectedNode
) {

    // ----------------------------------------
    // Clear previous graph selection
    // ----------------------------------------

    const graphNodes =
        componentGraph.querySelectorAll(
            ".graph-node"
        );

    graphNodes.forEach(function (node) {

        node.classList.remove(
            "active"
        );

    });


    // ----------------------------------------
    // Highlight selected graph node
    // ----------------------------------------

    if (selectedNode) {

        selectedNode.classList.add(
            "active"
        );

    }


    // ----------------------------------------
    // Find matching sidebar component
    // ----------------------------------------

    const sidebarItems =
        componentList.querySelectorAll(
            ".component-item"
        );

    let matchingSidebarItem = null;

    sidebarItems.forEach(function (item) {

        if (
            item.dataset.componentId ===
            component.id
        ) {

            matchingSidebarItem = item;

        }

    });


    // ----------------------------------------
    // Reuse our working Inspector selection
    // ----------------------------------------

    selectComponent(
        component,
        matchingSidebarItem
    );

}

// ============================================================
// COMPONENT SELECTION + BASIC INSPECTOR
// ============================================================

function selectComponent(component, selectedItem) {

    if (!component) {
        return;
    }


    // ----------------------------------------
    // Remove previous sidebar selection
    // ----------------------------------------

    const componentItems =
        componentList.querySelectorAll(
            ".component-item"
        );

    componentItems.forEach(function (item) {

        item.classList.remove(
            "active"
        );

    });


    // ----------------------------------------
    // Highlight selected component
    // ----------------------------------------

    if (selectedItem) {

        selectedItem.classList.add(
            "active"
        );

    }


    // ----------------------------------------
    // Hide empty Inspector
    // ----------------------------------------

    inspectorEmpty.classList.add(
        "hidden"
    );


    // ----------------------------------------
    // Show Inspector content
    // ----------------------------------------

    inspectorContent.classList.remove(
        "hidden"
    );


    // ----------------------------------------
    // Component name
    // ----------------------------------------

    componentName.textContent =
        component.name ||
        "Unnamed component";


    // ----------------------------------------
    // Scope
    // ----------------------------------------

    componentScope.textContent =
        (
            component.scope ||
            "unknown"
        ).toUpperCase();


    // ----------------------------------------
    // Evidence level
    // ----------------------------------------

    componentEvidence.textContent =
        (
            component.evidence_level ||
            "unknown"
        ).toUpperCase();


    // ----------------------------------------
    // Function
    // ----------------------------------------

    if (component.function) {

        componentFunction.textContent =
            component.function;

    }
    else {

        componentFunction.textContent =
            "Not specified in the retrieved documentation.";

    }

    renderComponentSources(
    component
    );

    renderComponentImage(
    component
    );


    console.log(
        "[SpecLayer] Selected component:",
        component
    );

}


// ============================================================
// COMPONENT SOURCE EVIDENCE
// ============================================================

function renderComponentSources(component) {

    componentSourceList.innerHTML = "";

    if (!component || !currentAnalysis) {
        return;
    }


    const sourceIds =
        Array.isArray(component.source_ids)
            ? component.source_ids
            : [];

    const allSources =
        Array.isArray(currentAnalysis.sources)
            ? currentAnalysis.sources
            : [];


    // ----------------------------------------
    // No evidence sources
    // ----------------------------------------

    if (sourceIds.length === 0) {

        const emptyMessage =
            document.createElement("p");

        emptyMessage.className =
            "source-evidence-empty";

        emptyMessage.textContent =
            "No supporting source was returned for this component.";

        componentSourceList.appendChild(
            emptyMessage
        );

        return;
    }


    // ----------------------------------------
    // Match source_ids to source objects
    // ----------------------------------------

    const matchedSources =
        sourceIds
            .map(function (sourceId) {

                return allSources.find(
                    function (source) {

                        return String(
                            source.source_id
                        ) === String(
                            sourceId
                        );

                    }
                );

            })
            .filter(Boolean);


    // ----------------------------------------
    // IDs exist but source objects do not
    // ----------------------------------------

    if (matchedSources.length === 0) {

        const emptyMessage =
            document.createElement("p");

        emptyMessage.className =
            "source-evidence-empty";

        emptyMessage.textContent =
            "Supporting source details are unavailable.";

        componentSourceList.appendChild(
            emptyMessage
        );

        return;
    }


    // ----------------------------------------
    // Render evidence sources
    // ----------------------------------------

    matchedSources.forEach(
        function (source) {

            const sourceItem =
                document.createElement("a");

            sourceItem.className =
                "component-source-item";


            if (source.url) {

                sourceItem.href =
                    source.url;

                sourceItem.target =
                    "_blank";

                sourceItem.rel =
                    "noopener noreferrer";

            }
            else {

                sourceItem.removeAttribute(
                    "href"
                );

            }


            const sourceLabel =
                document.createElement("span");

            sourceLabel.className =
                "component-source-label";

            sourceLabel.textContent =
                `SOURCE ${source.source_id}`;


            const sourceTitle =
                document.createElement("span");

            sourceTitle.className =
                "component-source-title";

            sourceTitle.textContent =
                source.title ||
                "Documentation source";


            const sourceArrow =
                document.createElement("span");

            sourceArrow.className =
                "material-symbols-outlined component-source-arrow";

            sourceArrow.textContent =
                "open_in_new";


            sourceItem.appendChild(
                sourceLabel
            );

            sourceItem.appendChild(
                sourceTitle
            );

            if (source.url) {

                sourceItem.appendChild(
                    sourceArrow
                );

            }


            componentSourceList.appendChild(
                sourceItem
            );

        }
    );

}


// ============================================================
// COMPONENT VISUAL REFERENCE
// ============================================================

function renderComponentImage(component) {
    if (!componentImageFrame) {
        return;
    }

    componentImageFrame.innerHTML = "";

    const media = component?.media;

    const imageUrl =
        media?.image_url ||
        media?.image?.image_url ||
        media?.thumbnail_url ||
        media?.image?.thumbnail_url ||
        null;

    if (!imageUrl) {
        const emptyState = document.createElement("div");
        emptyState.className = "component-image-empty";

        emptyState.innerHTML = `
            <span class="material-symbols-outlined">image</span>
            <span>No generic image available</span>
        `;

        componentImageFrame.appendChild(emptyState);
        return;
    }

    const image = document.createElement("img");

    image.className = "component-reference-image";
    image.src = imageUrl;
    image.alt = `Generic visual reference for ${component?.name || "component"}`;
    image.loading = "lazy";

    image.addEventListener("error", () => {
        componentImageFrame.innerHTML = `
            <div class="component-image-empty">
                <span class="material-symbols-outlined">broken_image</span>
                <span>Generic image could not be loaded</span>
            </div>
        `;
    });

    const disclaimer = document.createElement("div");
    disclaimer.className = "component-image-disclaimer";
    disclaimer.textContent =
        "Generic visual reference — not the exact device component.";

    componentImageFrame.appendChild(image);
    componentImageFrame.appendChild(disclaimer);
}

// ============================================================
// COMPONENT FILTERS
// ============================================================

function applyComponentFilter(filter) {

    if (!currentAnalysis) {
        return;
    }

    const analysis =
        currentAnalysis.analysis || {};

    const allComponents =
        Array.isArray(analysis.components)
            ? analysis.components
            : [];


    activeComponentFilter =
        filter || "all";


    // ----------------------------------------
    // Update active filter button
    // ----------------------------------------

    filterButtons.forEach(function (button) {

        const buttonFilter =
            button.dataset.filter;

        if (buttonFilter === activeComponentFilter) {

            button.classList.add(
                "active"
            );

        }
        else {

            button.classList.remove(
                "active"
            );

        }

    });


    // ----------------------------------------
    // Filter components
    // ----------------------------------------

    let visibleComponents =
        allComponents;

    if (activeComponentFilter !== "all") {

        visibleComponents =
            allComponents.filter(
                function (component) {

                    return component.scope ===
                        activeComponentFilter;

                }
            );

    }


    // ----------------------------------------
    // Re-render sidebar
    // ----------------------------------------

    renderComponentList(
        visibleComponents
    );


    // ----------------------------------------
    // Clear Inspector
    //
    // The previously selected component may
    // no longer be visible after filtering.
    // ----------------------------------------

    inspectorContent.classList.add(
        "hidden"
    );

    inspectorEmpty.classList.remove(
        "hidden"
    );


    console.log(
        "[SpecLayer] Component filter:",
        activeComponentFilter,
        "Visible:",
        visibleComponents.length
    );

}

filterButtons.forEach(function (button) {

    button.addEventListener(
        "click",
        function () {

            const filter =
                button.dataset.filter ||
                "all";

            applyComponentFilter(
                filter
            );

        }
    );

});

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