# Extra+ Repair Tool
# ==================
# This is a standalone repair tool for Extra+ submod.
# It will detect and fix incorrectly installed Extra+ files.
# After successful repair, you can safely delete this file.
#
# Author: ZeroFixer

#====Register the repair tool as a submod
init -990 python in mas_submod_utils:
    Submod(
        author="ZeroFixer",
        name="Extra Plus Repair",
        description="Detects and repairs incorrect submod installation. Once the ExtraPlus submod has been repaired, delete the EP Repair folder when MAS is closed.",
        version="1.0.0",
        settings_pane="_ep_repair_settings"
    )

init -999 python:
    import os
    import shutil
    
    # Configuration
    EP_REPAIR_DEBUG = False
    
    def ep_repair_log(message):
        """Log messages for debugging"""
        if EP_REPAIR_DEBUG:
            print("[EP Repair] " + str(message))
    
    def ep_repair_normalize_path(path):
        """Normalizes a path by replacing '\\' with '/' for compatibility."""
        return path.replace("\\", "/")
    
    def ep_repair_find_submods_folder(game_dir):
        """
        Case-insensitively finds the 'submods' folder.
        Returns the actual folder name as it exists on disk.
        """
        try:
            for folder in os.listdir(game_dir):
                if folder.lower() == "submods" and os.path.isdir(os.path.join(game_dir, folder)):
                    return folder
        except Exception:
            pass
        return "Submods"  # Default value if not found
    
    def ep_repair_find_broken_installs():
        """
        Scans the submods folder for incorrectly installed Extra+ files.
        Returns a list of dicts with broken_path, correct_path, parent_folder
        """
        broken_installs = []
        
        # Get the game directory
        game_dir = renpy.config.gamedir
        
        # Find the actual submods folder name (case-insensitive)
        submods_folder_name = ep_repair_find_submods_folder(game_dir)
        submods_dir = os.path.join(game_dir, submods_folder_name)
        correct_path = os.path.join(submods_dir, "ExtraPlus")
        
        if not os.path.exists(submods_dir):
            ep_repair_log("submods folder not found")
            return broken_installs
        
        # Files that identify Extra+ installation
        ep_signature_files = [
            "Extra_Plus_Main.rpy",
            "Extra_Plus_Labels.rpy",
            "Extra_Plus_Misc.rpy"
        ]
        
        # Folder name patterns that indicate Extra+ (case-insensitive)
        ep_folder_patterns = [
            "extraplus",
            "extra+",
            "extra_plus",
            "extra plus",
        ]
        
        def is_extraplus_folder_name(folder_name):
            """Check if folder name matches Extra+ patterns"""
            name_lower = folder_name.lower()
            for pattern in ep_folder_patterns:
                if name_lower == pattern or name_lower.startswith(pattern + " ") or name_lower.startswith(pattern + ".") or name_lower.startswith(pattern + "-") or name_lower.startswith(pattern + "_"):
                    return True
            return False
        
        def has_extraplus_files(folder_path):
            """Check if a folder contains Extra+ signature files"""
            try:
                for sig_file in ep_signature_files:
                    if os.path.exists(os.path.join(folder_path, sig_file)):
                        return True
            except:
                pass
            return False
        
        def find_extraplus_folders(search_path, depth=0):
            """
            Recursively search for folders containing Extra+ files.
            Returns list of paths to ExtraPlus folders in wrong locations.
            """
            results = []
            
            if depth > 8:  # Prevent infinite recursion
                return results
            
            try:
                for item in os.listdir(search_path):
                    item_path = os.path.join(search_path, item)
                    
                    if not os.path.isdir(item_path):
                        continue
                    
                    # Skip the correct ExtraPlus folder
                    if os.path.normcase(os.path.normpath(item_path)) == os.path.normcase(os.path.normpath(correct_path)):
                        continue
                    
                    # Check if this folder has Extra+ files directly
                    if has_extraplus_files(item_path):
                        ep_repair_log("Found Extra+ files in: {}".format(item_path))
                        results.append(item_path)
                    # Check if folder name matches Extra+ pattern and has nested structure
                    elif is_extraplus_folder_name(item) and depth == 0:
                        # This might be a ZIP folder like "Extra+ BETA 3 (1.4.1)"
                        ep_repair_log("Found Extra+ named folder: {}".format(item_path))
                        nested = find_extraplus_folders(item_path, depth + 1)
                        results.extend(nested)
                    else:
                        # Search inside this folder
                        nested = find_extraplus_folders(item_path, depth + 1)
                        results.extend(nested)
                        
            except Exception as e:
                ep_repair_log("Error scanning {}: {}".format(search_path, e))
            
            return results
        
        # Start search from submods folder
        broken_paths = find_extraplus_folders(submods_dir)
        
        for broken_path in broken_paths:
            # Find the top-level folder in submods that contains this broken install
            relative_to_submods = os.path.relpath(broken_path, submods_dir)
            top_folder = relative_to_submods.split(os.sep)[0]
            top_folder_path = os.path.join(submods_dir, top_folder)
            
            broken_installs.append({
                "broken_path": broken_path,
                "correct_path": correct_path,
                "parent_folder": os.path.dirname(broken_path),
                "top_folder": top_folder_path
            })
        
        ep_repair_log("Found {} broken installs".format(len(broken_installs)))
        return broken_installs
    
    def ep_repair_fix_installation(broken_install):
        """
        Moves files from broken location to correct location.
        Also moves mod_assets folder if present.
        Returns (success, message)
        """
        broken_path = broken_install["broken_path"]
        correct_path = broken_install["correct_path"]
        
        try:
            # Check if correct path already has files
            if os.path.exists(correct_path):
                # Check if it has actual Extra+ files
                has_files = False
                for f in os.listdir(correct_path):
                    if f.endswith(".rpy"):
                        has_files = True
                        break
                
                if has_files:
                    # Backup existing and replace
                    backup_path = correct_path + "_backup"
                    if os.path.exists(backup_path):
                        shutil.rmtree(backup_path)
                    shutil.move(correct_path, backup_path)
            
            # Move broken installation to correct location
            shutil.move(broken_path, correct_path)
            
            # Check for mod_assets folder in the broken structure
            # Path like: Extra+ BETA 3 (1.4.1)/game/mod_assets
            broken_parent = broken_install["parent_folder"]  # This is .../game/submods
            broken_game_folder = os.path.dirname(broken_parent)  # This is .../game
            broken_mod_assets = os.path.join(broken_game_folder, "mod_assets")
            
            if os.path.exists(broken_mod_assets) and os.path.isdir(broken_mod_assets):
                # Move mod_assets to correct location (game/mod_assets)
                correct_mod_assets = os.path.join(renpy.config.gamedir, "mod_assets")
                
                def merge_directories(src_dir, dst_dir):
                    """Recursively merge src_dir into dst_dir"""
                    if not os.path.exists(dst_dir):
                        os.makedirs(dst_dir)
                    
                    for item in os.listdir(src_dir):
                        src_path = os.path.join(src_dir, item)
                        dst_path = os.path.join(dst_dir, item)
                        
                        if os.path.isdir(src_path):
                            # Recursively merge subdirectories
                            merge_directories(src_path, dst_path)
                        else:
                            # Copy file (overwrite if exists, or create new)
                            if not os.path.exists(dst_path):
                                shutil.copy2(src_path, dst_path)
                
                # Merge the mod_assets folders
                merge_directories(broken_mod_assets, correct_mod_assets)
                
                # Now safely remove the source after successful merge
                try:
                    shutil.rmtree(broken_mod_assets)
                except:
                    pass
            
            # Try to clean up empty parent folders
            parent = broken_install["parent_folder"]
            game_submods = os.path.join(renpy.config.gamedir, ep_repair_find_submods_folder(renpy.config.gamedir))
            while parent and parent != game_submods:
                try:
                    if os.path.isdir(parent) and not os.listdir(parent):
                        os.rmdir(parent)
                        parent = os.path.dirname(parent)
                    else:
                        break
                except:
                    break
            
            # Also try to clean up the top-level broken folder (the ZIP folder)
            top_folder = broken_install.get("top_folder")
            if top_folder and os.path.exists(top_folder):
                try:
                    # Files that are safe to delete (non-essential)
                    safe_to_delete_files = [
                        "readme.txt", "readme.md", "readme",
                        "license.txt", "license.md", "license",
                        "changelog.txt", "changelog.md", "changelog",
                        ".ds_store", "thumbs.db", "desktop.ini"
                    ]
                    
                    def is_safe_to_delete(path):
                        """Check if folder only contains safe-to-delete files"""
                        if not os.path.isdir(path):
                            return False
                        for item in os.listdir(path):
                            item_path = os.path.join(path, item)
                            if os.path.isfile(item_path):
                                # Check if it's a safe file
                                if item.lower() not in safe_to_delete_files:
                                    return False
                            elif os.path.isdir(item_path):
                                # Recursively check subdirectories
                                if not is_safe_to_delete(item_path):
                                    return False
                        return True
                    
                    if is_safe_to_delete(top_folder):
                        shutil.rmtree(top_folder)
                except:
                    pass
            
            return (True, "Successfully moved Extra+ to correct location!")
            
        except Exception as e:
            return (False, "Error during repair: {}".format(str(e)))

# Store results
default ep_repair_results = None
default ep_repair_checked = False

init python:
    def ep_repair_run_check():
        """Run the repair check and store results"""
        store.ep_repair_results = ep_repair_find_broken_installs()
        store.ep_repair_checked = True
        renpy.restart_interaction()
    
    def ep_repair_do_repair():
        """Execute the repair for all broken installations"""
        if not store.ep_repair_results:
            return
        
        success_count = 0
        fail_count = 0
        
        for install in store.ep_repair_results:
            success, msg = ep_repair_fix_installation(install)
            if success:
                success_count += 1
            else:
                fail_count += 1
        
        if fail_count == 0:
            renpy.notify("Repaired {} installation(s)! Please restart the game.".format(success_count))
        else:
            renpy.notify("Repaired {}, failed {}. Check manually.".format(success_count, fail_count))
        
        # Clear results after repair
        store.ep_repair_results = None
        store.ep_repair_checked = False
        renpy.restart_interaction()

# Settings pane for the submod
screen _ep_repair_settings():
    $ tooltip = renpy.get_screen("submods", "screens").scope["tooltip"]
    
    vbox:
        box_wrap False
        xfill True
        xmaximum 800
        
        hbox:
            style_prefix "check"
            box_wrap False
            
            textbutton _("Check Installation"):
                action Function(ep_repair_run_check)
                hovered tooltip.Action("Scan for incorrectly installed Extra+ files")
        
        null height 10
        
        if ep_repair_checked:
            if ep_repair_results:
                text _("(!) Found {} problem(s):").format(len(ep_repair_results)):
                    size 14
                    color "#f88"
                
                null height 5
                
                for install in ep_repair_results:
                    text "  - {}".format(install["broken_path"]):
                        size 12
                        color "#faa"
                
                null height 10
                
                hbox:
                    style_prefix "check"
                    textbutton _("Repair Now"):
                        action Function(ep_repair_do_repair)
                        hovered tooltip.Action("Move files to the correct location")
            else:
                text _("(OK) No problems found! Extra+ is installed correctly."):
                    size 14
                    color "#8f8"
        else:
            text _("Click 'Check Installation' to scan for problems."):
                size 14
                color "#aaa"
