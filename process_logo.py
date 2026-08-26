import cv2
import numpy as np

# Load image
img = cv2.imread(r"D:\iris-frontend\public\PROCAMBRIAN_FULL_LOGO.jpeg", cv2.IMREAD_UNCHANGED)
if img is not None:
    # Convert to RGBA
    if img.shape[2] == 3:
        b, g, r = cv2.split(img)
        alpha = np.ones(b.shape, dtype=b.dtype) * 255
        rgba = cv2.merge([b, g, r, alpha])
    else:
        rgba = img

    # Find white/near-white pixels (e.g. RGB > 240) and make them transparent
    # or crop bounding box of the non-white content
    gray = cv2.cvtColor(rgba[:,:,:3], cv2.COLOR_BGR2GRAY)
    mask = gray < 245  # content pixels

    # Find bounding box to crop huge empty margins
    coords = cv2.findNonZero(mask.astype(np.uint8))
    x, y, w, h = cv2.boundingRect(coords)

    # Crop tightly to the logo content
    cropped = rgba[y:y+h, x:x+w]

    # Make white background transparent
    b, g, r, a = cv2.split(cropped)
    gray_cropped = cv2.cvtColor(cropped[:,:,:3], cv2.COLOR_BGR2GRAY)
    
    # Soft alpha for near white
    alpha_mask = np.where(gray_cropped >= 250, 0, 255).astype(np.uint8)
    cropped[:, :, 3] = alpha_mask

    cv2.imwrite(r"D:\iris-frontend\public\PROCAMBRIAN_FULL_LOGO.png", cropped)
    print(f"Saved tightly cropped transparent logo: {w}x{h}")
