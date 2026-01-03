# Remaining Tasks - Video Editor

## 🎯 High Priority (Should Do Soon)

### 1. Parallel Batch Processing
**Status:** Not Started  
**Priority:** High  
**Effort:** Medium (2-3 days)

**Description:**
- Currently processes videos sequentially (one at a time)
- Should use multiprocessing pool to process multiple videos simultaneously
- Configurable worker count (based on CPU cores)
- Progress tracking per file

**Implementation Notes:**
- Use `multiprocessing.Pool` or `concurrent.futures.ProcessPoolExecutor`
- Need to handle GPU encoding carefully (may need to limit concurrent GPU operations)
- Update BatchWindow to show progress for multiple files
- Consider memory constraints when processing large files in parallel

---

### 2. BatchWindow UI Improvements
**Status:** Not Started  
**Priority:** High  
**Effort:** Low (1 day)

**Description:**
- Apply the same structured label-based UI to BatchWindow
- Currently uses text widget, should use static parameter labels + dynamic progress labels
- Better organization and readability during batch processing

**Implementation Notes:**
- Similar structure to VideoScalerWindow
- Show batch-level parameters (encoding settings, folder paths)
- Show per-file progress or overall batch progress
- Consider showing progress for current file being processed

---

## 📋 Medium Priority (Nice to Have)

### 3. Integration of Advanced Encoding Options
**Status:** Partially Complete  
**Priority:** Medium  
**Effort:** Medium (2-3 days)

**Description:**
- Audio/video codec selection dialogs exist but may not be fully integrated
- Make these options easily accessible from main encoding flow
- Add to EncodingSettingsDialog or create separate advanced settings section

**Current State:**
- ✅ AudioCodecDialog exists
- ✅ AudioBitrateDialog exists
- ✅ VideoCodecDialog exists
- ⏳ Need to integrate into main encoding workflow

---

### 4. Two-Pass Encoding
**Status:** Not Started  
**Priority:** Medium  
**Effort:** Medium (2-3 days)

**Description:**
- Add option for two-pass encoding
- Better quality control for target file sizes
- First pass analyzes video, second pass encodes with optimal settings

**Implementation Notes:**
- Add checkbox/option in EncodingSettingsDialog
- Modify FFmpegCommandBuilder to support two-pass commands
- Update VideoProcessor to handle two-pass encoding flow
- Show progress for both passes

---

### 5. Bitrate Control Option
**Status:** Not Started  
**Priority:** Medium  
**Effort:** Low-Medium (1-2 days)

**Description:**
- Alternative to CRF for precise file size control
- Allow users to specify target bitrate (e.g., 2 Mbps, 5 Mbps)
- Useful when file size is more important than quality

**Implementation Notes:**
- Add bitrate input field to EncodingSettingsDialog
- Make it mutually exclusive with CRF (radio buttons or similar)
- Update FFmpegCommandBuilder to use `-b:v` instead of `-crf`
- Add validation for bitrate values

---

## 🔧 Low Priority (Future Enhancements)

### 6. Video Filters
**Status:** Not Started  
**Priority:** Low  
**Effort:** Medium (3-4 days)

**Description:**
- Brightness, contrast, saturation, sharpness adjustments
- Add filter dialog or sliders in encoding settings
- Apply filters via FFmpeg filter_complex

**Implementation Notes:**
- Create VideoFiltersDialog
- Use FFmpeg filter syntax (e.g., `eq=brightness=0.1:contrast=1.2`)
- Preview would be helpful but complex to implement

---

### 7. Crop/Trim Functionality
**Status:** Not Started  
**Priority:** Low  
**Effort:** High (1 week+)

**Description:**
- Select video regions to crop
- Trim clips (select start/end time)
- Visual selection interface would be ideal

**Implementation Notes:**
- Requires video preview/thumbnail generation
- Complex UI for region selection
- FFmpeg crop and trim filters
- Consider using external library for video preview

---

### 8. Watermark Support
**Status:** Not Started  
**Priority:** Low  
**Effort:** Medium (2-3 days)

**Description:**
- Add text watermarks
- Add image watermarks
- Position and opacity controls

**Implementation Notes:**
- Add watermark options to EncodingSettingsDialog
- Use FFmpeg overlay filter
- Support text (with font selection) and image watermarks
- Position options (top-left, top-right, bottom-left, bottom-right, center)

---

### 9. Enhanced Preview
**Status:** Partially Complete  
**Priority:** Low  
**Effort:** Medium (3-4 days)

**Description:**
- PreviewWindow exists but could be enhanced
- Add thumbnail generation
- Show video preview before encoding
- Preview with applied filters/effects

**Current State:**
- ✅ PreviewWindow shows video info and settings
- ❌ No thumbnail generation
- ❌ No video preview playback

---

### 10. Pause/Resume Functionality
**Status:** Not Started  
**Priority:** Low  
**Effort:** High (1 week+)

**Description:**
- Pause encoding operation
- Resume from where it left off
- Save encoding state

**Implementation Notes:**
- Complex to implement with FFmpeg
- May require checkpointing or partial file handling
- Consider if worth the complexity vs. just canceling and restarting

---

### 11. Queue System
**Status:** Not Started  
**Priority:** Low  
**Effort:** Medium (3-4 days)

**Description:**
- Queue multiple videos for processing
- Process them sequentially or in parallel
- Reorder, remove items from queue
- Save/load queue

**Implementation Notes:**
- Create QueueWindow or add to main interface
- Queue data structure to hold video files and settings
- Integration with existing processing windows

---

## 📊 Summary

**Total High Priority Tasks:** 2  
**Total Medium Priority Tasks:** 3  
**Total Low Priority Tasks:** 6

**Estimated Total Effort:**
- High Priority: ~3-4 days
- Medium Priority: ~5-8 days
- Low Priority: ~3-4 weeks

**Recommended Next Steps:**
1. Start with **Parallel Batch Processing** (biggest performance improvement)
2. Then **BatchWindow UI Improvements** (quick win, better UX)
3. Then work through Medium priority items based on user feedback

---

**Last Updated:** Current session  
**Note:** This document should be updated as tasks are completed or priorities change.

