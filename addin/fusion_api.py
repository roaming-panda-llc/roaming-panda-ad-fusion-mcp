"""Fusion 360 API wrapper functions for MCP server."""

import adsk.core
import adsk.fusion
import base64
import os
import tempfile


def get_app():
    """Get the Fusion 360 application object."""
    return adsk.core.Application.get()


def get_document_info():
    """Get information about the active document."""
    app = get_app()
    if not app:
        return {"error": "Fusion 360 not running"}

    doc = app.activeDocument
    if not doc:
        return {"error": "No active document", "documents_open": app.documents.count}

    design = adsk.fusion.Design.cast(app.activeProduct)

    info = {
        "name": doc.name,
        "is_saved": doc.isSaved,
        "data_file": None,
        "product_type": app.activeProduct.productType if app.activeProduct else None,
    }

    if doc.dataFile:
        info["data_file"] = {
            "name": doc.dataFile.name,
            "id": doc.dataFile.id,
            "version": doc.dataFile.versionNumber,
        }

    if design:
        info["design"] = {
            "design_type": "parametric" if design.designType == 0 else "direct",
            "units": design.unitsManager.defaultLengthUnits,
            "component_count": design.allComponents.count,
            "body_count": design.rootComponent.bRepBodies.count,
        }

    return info


def get_component_tree():
    """Get hierarchical component structure."""
    app = get_app()
    if not app or not app.activeDocument:
        return {"error": "No active document"}

    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        return {"error": "Active document is not a design"}

    def process_component(comp, depth=0):
        result = {
            "name": comp.name,
            "bodies": comp.bRepBodies.count,
            "sketches": comp.sketches.count,
            "occurrences": [],
        }

        if depth < 5:  # Limit recursion depth
            for occ in comp.occurrences:
                child = process_component(occ.component, depth + 1)
                child["occurrence_name"] = occ.name
                child["is_visible"] = occ.isVisible
                result["occurrences"].append(child)

        return result

    return {
        "root_component": process_component(design.rootComponent),
        "total_components": design.allComponents.count,
    }


def get_sketch_info(sketch_name=None):
    """Get information about sketches in the active component."""
    app = get_app()
    if not app or not app.activeDocument:
        return {"error": "No active document"}

    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        return {"error": "Active document is not a design"}

    root = design.rootComponent
    sketches_info = []

    for sketch in root.sketches:
        if sketch_name and sketch.name != sketch_name:
            continue

        sketch_data = {
            "name": sketch.name,
            "is_fully_constrained": sketch.isFullyConstrained,
            "profile_count": sketch.profiles.count,
            "curves_count": sketch.sketchCurves.count,
            "dimensions_count": sketch.sketchDimensions.count,
            "constraints_count": sketch.geometricConstraints.count,
        }

        # Get dimension values
        dimensions = []
        for dim in sketch.sketchDimensions:
            dim_info = {"name": dim.name if hasattr(dim, "name") else "unnamed"}
            if hasattr(dim, "parameter") and dim.parameter:
                dim_info["value"] = dim.parameter.value
                dim_info["expression"] = dim.parameter.expression
                dim_info["unit"] = dim.parameter.unit
            dimensions.append(dim_info)
        sketch_data["dimensions"] = dimensions

        sketches_info.append(sketch_data)

    if sketch_name and not sketches_info:
        return {"error": f"Sketch '{sketch_name}' not found"}

    return {"sketches": sketches_info}


def get_body_info(body_name=None):
    """Get information about bodies in the design."""
    app = get_app()
    if not app or not app.activeDocument:
        return {"error": "No active document"}

    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        return {"error": "Active document is not a design"}

    bodies_info = []

    for comp in design.allComponents:
        for body in comp.bRepBodies:
            if body_name and body.name != body_name:
                continue

            bbox = body.boundingBox
            body_data = {
                "name": body.name,
                "component": comp.name,
                "is_solid": body.isSolid,
                "is_visible": body.isVisible,
                "face_count": body.faces.count,
                "edge_count": body.edges.count,
                "vertex_count": body.vertices.count,
            }

            if bbox:
                body_data["bounding_box"] = {
                    "min": [bbox.minPoint.x, bbox.minPoint.y, bbox.minPoint.z],
                    "max": [bbox.maxPoint.x, bbox.maxPoint.y, bbox.maxPoint.z],
                }

            # Try to get volume and area (may fail for non-solid bodies)
            try:
                props = body.physicalProperties
                body_data["volume_cm3"] = props.volume
                body_data["area_cm2"] = props.area
            except Exception:
                pass

            bodies_info.append(body_data)

    if body_name and not bodies_info:
        return {"error": f"Body '{body_name}' not found"}

    return {"bodies": bodies_info}


def export_screenshot():
    """Export a screenshot of the current viewport."""
    app = get_app()
    if not app or not app.activeDocument:
        return {"error": "No active document"}

    viewport = app.activeViewport
    if not viewport:
        return {"error": "No active viewport"}

    # Create temp file path
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, "fusion_mcp_screenshot.png")

    try:
        # Save image to temp file
        success = viewport.saveAsImageFile(temp_path, 1920, 1080)
        if not success:
            return {"error": "Failed to save screenshot"}

        # Read and encode as base64
        with open(temp_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        # Clean up temp file
        os.remove(temp_path)

        return {
            "format": "png",
            "width": 1920,
            "height": 1080,
            "data_base64": image_data,
        }
    except Exception as e:
        return {"error": f"Screenshot failed: {str(e)}"}


def get_parameters():
    """Get all user parameters in the design."""
    app = get_app()
    if not app or not app.activeDocument:
        return {"error": "No active document"}

    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        return {"error": "Active document is not a design"}

    params = []
    for param in design.userParameters:
        params.append({
            "name": param.name,
            "expression": param.expression,
            "value": param.value,
            "unit": param.unit,
            "comment": param.comment,
        })

    return {"user_parameters": params, "count": len(params)}


def run_script(code: str):
    """Execute arbitrary Python code in Fusion context.

    The code has access to:
    - adsk: The Fusion 360 API module
    - app: The Application object
    - design: The active Design object
    - ui: The UserInterface object
    - result: Set this to return data to the caller

    Args:
        code: Python code to execute

    Returns:
        dict with 'success' and 'result', or 'error' on failure
    """
    app = get_app()
    if not app:
        return {"error": "Fusion 360 not running"}

    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        return {"error": "No active design"}

    # Create namespace with Fusion modules
    namespace = {
        "adsk": adsk,
        "app": app,
        "design": design,
        "ui": app.userInterface,
        "result": None
    }

    try:
        exec(code, namespace)
        return {"success": True, "result": namespace.get("result")}
    except Exception as e:
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}


def create_sketch(component_name: str = None, plane: str = "XY"):
    """Create a new sketch on the specified construction plane.

    Args:
        component_name: Component to create sketch in (None or "root" for root component)
        plane: Construction plane - "XY", "XZ", or "YZ"

    Returns:
        dict with 'sketch_name' on success, or 'error' on failure
    """
    app = get_app()
    if not app or not app.activeDocument:
        return {"error": "No active document"}

    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        return {"error": "Active document is not a design"}

    try:
        # Get the component
        if component_name and component_name != "root":
            component = None
            for comp in design.allComponents:
                if comp.name == component_name:
                    component = comp
                    break
            if not component:
                return {"error": f"Component '{component_name}' not found"}
        else:
            component = design.rootComponent

        # Get the construction plane
        plane = plane.upper()
        if plane == "XY":
            construction_plane = component.xYConstructionPlane
        elif plane == "XZ":
            construction_plane = component.xZConstructionPlane
        elif plane == "YZ":
            construction_plane = component.yZConstructionPlane
        else:
            return {"error": f"Invalid plane '{plane}'. Use 'XY', 'XZ', or 'YZ'"}

        # Create the sketch
        sketch = component.sketches.add(construction_plane)

        return {"success": True, "sketch_name": sketch.name}

    except Exception as e:
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}


def activate_component(name: str):
    """Activate a component by name for editing.

    Args:
        name: Component name to activate

    Returns:
        dict with 'success' on success, or 'error' on failure
    """
    app = get_app()
    if not app or not app.activeDocument:
        return {"error": "No active document"}

    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        return {"error": "Active document is not a design"}

    try:
        # Find the component
        component = None
        for comp in design.allComponents:
            if comp.name == name:
                component = comp
                break

        if not component:
            return {"error": f"Component '{name}' not found"}

        # Activate it
        design.activeComponent = component

        return {"success": True, "component_name": component.name}

    except Exception as e:
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}


def draw_circle(sketch_name: str, center_x: float, center_y: float, radius: float):
    """Draw a circle in the specified sketch.

    Args:
        sketch_name: Name of sketch to draw in
        center_x: X coordinate of center (cm)
        center_y: Y coordinate of center (cm)
        radius: Radius of circle (cm)

    Returns:
        dict with 'success' on success, or 'error' on failure
    """
    app = get_app()
    if not app or not app.activeDocument:
        return {"error": "No active document"}

    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        return {"error": "Active document is not a design"}

    try:
        # Find the sketch
        sketch = None
        for comp in design.allComponents:
            for sk in comp.sketches:
                if sk.name == sketch_name:
                    sketch = sk
                    break
            if sketch:
                break

        if not sketch:
            return {"error": f"Sketch '{sketch_name}' not found"}

        # Draw the circle
        center = adsk.core.Point3D.create(center_x, center_y, 0)
        circle = sketch.sketchCurves.sketchCircles.addByCenterRadius(center, radius)

        return {"success": True, "sketch_name": sketch_name}

    except Exception as e:
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}


def draw_rectangle(sketch_name: str, x1: float, y1: float, x2: float, y2: float):
    """Draw a rectangle in the specified sketch.

    Args:
        sketch_name: Name of sketch to draw in
        x1: X coordinate of first corner (cm)
        y1: Y coordinate of first corner (cm)
        x2: X coordinate of second corner (cm)
        y2: Y coordinate of second corner (cm)

    Returns:
        dict with 'success' on success, or 'error' on failure
    """
    app = get_app()
    if not app or not app.activeDocument:
        return {"error": "No active document"}

    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        return {"error": "Active document is not a design"}

    try:
        # Find the sketch
        sketch = None
        for comp in design.allComponents:
            for sk in comp.sketches:
                if sk.name == sketch_name:
                    sketch = sk
                    break
            if sketch:
                break

        if not sketch:
            return {"error": f"Sketch '{sketch_name}' not found"}

        # Draw the rectangle
        point1 = adsk.core.Point3D.create(x1, y1, 0)
        point2 = adsk.core.Point3D.create(x2, y2, 0)
        rect = sketch.sketchCurves.sketchLines.addTwoPointRectangle(point1, point2)

        return {"success": True, "sketch_name": sketch_name}

    except Exception as e:
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}


def extrude(sketch_name: str, profile_index: int, distance: float, operation: str = "new"):
    """Create an extrusion from a sketch profile.

    Args:
        sketch_name: Name of sketch containing profile
        profile_index: Index of profile to extrude (0-based)
        distance: Distance to extrude (cm)
        operation: "new", "join", or "cut"

    Returns:
        dict with 'feature_name' on success, or 'error' on failure
    """
    app = get_app()
    if not app or not app.activeDocument:
        return {"error": "No active document"}

    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        return {"error": "Active document is not a design"}

    try:
        # Find the sketch
        sketch = None
        component = None
        for comp in design.allComponents:
            for sk in comp.sketches:
                if sk.name == sketch_name:
                    sketch = sk
                    component = comp
                    break
            if sketch:
                break

        if not sketch:
            return {"error": f"Sketch '{sketch_name}' not found"}

        # Get the profile
        if profile_index < 0 or profile_index >= sketch.profiles.count:
            return {"error": f"Profile index {profile_index} out of range (0-{sketch.profiles.count - 1})"}

        profile = sketch.profiles.item(profile_index)

        # Map operation string to Fusion enum
        operation_map = {
            "new": adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
            "join": adsk.fusion.FeatureOperations.JoinFeatureOperation,
            "cut": adsk.fusion.FeatureOperations.CutFeatureOperation
        }

        if operation not in operation_map:
            return {"error": f"Invalid operation '{operation}'. Use 'new', 'join', or 'cut'"}

        # Create the extrusion
        extrudes = component.features.extrudeFeatures
        distance_input = adsk.core.ValueInput.createByReal(distance)
        extrude_input = extrudes.createInput(profile, operation_map[operation])
        extrude_input.setDistanceExtent(False, distance_input)
        extrude_feature = extrudes.add(extrude_input)

        return {"success": True, "feature_name": extrude_feature.name}

    except Exception as e:
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}


def set_visibility(component_name: str, visible: bool):
    """Set visibility of a component.

    Args:
        component_name: Name of component
        visible: True to show, False to hide

    Returns:
        dict with 'success' on success, or 'error' on failure
    """
    app = get_app()
    if not app or not app.activeDocument:
        return {"error": "No active document"}

    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        return {"error": "Active document is not a design"}

    try:
        # Find the component
        component = None
        for comp in design.allComponents:
            if comp.name == component_name:
                component = comp
                break

        if not component:
            return {"error": f"Component '{component_name}' not found"}

        # Set visibility
        component.isBodiesFolderLightBulbOn = visible

        return {"success": True, "component_name": component_name, "visible": visible}

    except Exception as e:
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}


def list_versions():
    """List all saved versions of the current document.

    Returns:
        dict with document_name, current_version, total_versions, and versions list
        Each version has: version_number, version_id, name, date_created

    Note: Only works for cloud-saved documents (not local files)
    """
    app = get_app()
    if not app or not app.activeDocument:
        return {"error": "No active document"}

    doc = app.activeDocument
    if not doc.dataFile:
        return {"error": "Document not saved to cloud (no version history)"}

    data_file = doc.dataFile
    versions_collection = data_file.versions

    versions = []
    for i in range(versions_collection.count):
        version = versions_collection.item(i)
        versions.append({
            "version_number": version.versionNumber,
            "version_id": version.id,
            "name": version.name,
            "date_created": version.dateCreated.isoformat() if version.dateCreated else None,
            "description": version.description if hasattr(version, 'description') else None
        })

    return {
        "document_name": doc.name,
        "current_version": data_file.versionNumber,
        "total_versions": versions_collection.count,
        "versions": versions
    }


def restore_version(version_number: int):
    """Open a specific version of the document in a new tab.

    To make this version the current version, save it after it opens.

    Args:
        version_number: The version number to restore (1-based)

    Returns:
        dict with success status and note about saving
    """
    app = get_app()
    if not app or not app.activeDocument:
        return {"error": "No active document"}

    doc = app.activeDocument
    if not doc.dataFile:
        return {"error": "Document not saved to cloud (no version history)"}

    data_file = doc.dataFile
    versions_collection = data_file.versions

    # Find the target version
    target_version = None
    for i in range(versions_collection.count):
        version = versions_collection.item(i)
        if version.versionNumber == version_number:
            target_version = version
            break

    if not target_version:
        return {"error": f"Version {version_number} not found"}

    try:
        # Open the version - this opens it in a new tab
        opened_doc = app.documents.open(target_version)
        if opened_doc:
            return {
                "success": True,
                "opened_document": opened_doc.name,
                "version_number": version_number,
                "note": "Version opened in new tab. Save to make it the current version."
            }
        else:
            return {"error": "Failed to open version"}
    except Exception as e:
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}
