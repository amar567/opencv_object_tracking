# quick and dirty version of object tracking for a very specific use case.
# there are many assumptios in this code i will mention them as we preoceed


# Import all the required libraries/packages
import cv2
import numpy as np

# Crop a region of interest (ROI) from the frame in original resolution
h = 800
v = 120
box_size = 1360
# resize the ROI box to
resize_box_to = 900
# Define the radius of the circle ROI at center of the frame - specific to our case
radius = 440 # Adjust this value as needed
# setting output fps 
output_fps = 60  # same as input in this case
# thresholds for detecting reflection of top lamp in our case
lower_bound = 110
upper_bound = 255
# determined using contour length distribution
contour_length_cut_off = 70 # contour lenght cutoff depends on sample here weve experimentally determined
# approx Bead radius depends case by case
apprx_bead_radius = 45

# reading the video 
source = cv2.VideoCapture('dark_bg.mp4')

# set the output video params - here we save it as mp4
size = (resize_box_to, resize_box_to)
result = cv2.VideoWriter('gray.mp4',  
            cv2.VideoWriter_fourcc(*'MP4V'), 
            output_fps, size, 0)

# Totl nuber of frames in video
totFrames = source.get(cv2.CAP_PROP_FRAME_COUNT)

# initializing some variables
# coordinates
cord_list = []
# all contours sizes
size_dist = []

# find dist between 2 pts
def dist(i,j):
    # print(i,j)
    point1 = np.array(i,dtype=int)
    point2 = np.array(j,dtype=int)

    return int(np.ceil(np.linalg.norm(point1 - point2)))
    return 46

# running the loop 
for fno in range(int(totFrames)):

    print("processing frame no "+str(fno))

    # extracting the frames 
    source.set(cv2.CAP_PROP_POS_FRAMES, fno)
    ret, img = source.read()

    # If the frame was not read successfully, break the loop
    if not ret:
        break

    # setting region of interest for the input video - assumed suqare
    # original video resolution is 2720 × 1520 in this case
    roi = img[v:(v+box_size),h:h+box_size]

    # Resize the ROI to a specific size (e.g., 200x200)
    roi_resized = cv2.resize(roi, (resize_box_to, resize_box_to))

    # converting to gray-scale 
    gray = cv2.cvtColor(roi_resized, cv2.COLOR_BGR2GRAY)

    # Read the image
    image = gray  # redundant

    # Get the dimensions of the image
    height, width = image.shape[:2]

    # print(height,width)

    # Create a black mask with the same dimensions as the image
    mask = np.zeros((height, width), np.uint8)

    # Calculate the center of the image
    center = (width // 2 , height // 2 )

    # Draw a solid white circle on the mask
    cv2.circle(mask, center, radius, 255, -1)

    # Apply the mask to the image
    masked_image = cv2.bitwise_and(image, image, mask=mask)

    # we apply thresholding to a copy of this image then find the contours where this thresholded image changes from black to white
    ret, thresh = cv2.threshold(masked_image, lower_bound, upper_bound, 0)
    contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    # # finding cutoff for the contour length
    # for cont in contours:
    #     size_dist.append(np.shape(cont)[0])

    # we will find some smaller contours here and there so remove the smaller and larger ones as required 
    filtered_arrays = [array for array in contours if len(array) >= contour_length_cut_off]

    # ##########################
    # contours in our case are somewhat round and center of mass of the contour can approximate the position of center of the bead

    # Store all the centers of these contours
    contour_centers = []

    # find center of mass of each contour
    for i in range(len(filtered_arrays)):
        kpCnt = len(filtered_arrays[i])

        x = 0
        y = 0

        for kp in filtered_arrays[i]:
            x = x+kp[0][0]
            y = y+kp[0][1]
        # print(x/kpCnt,y/kpCnt)

        x_com,y_com = (np.uint16(np.ceil(x/kpCnt)),np.uint16(np.ceil(y/kpCnt)))
        contour_centers.append([x_com, y_com])

    cleaned_contour_centers = []

    # check any overlapping contours whose centers are closer than radius of beads 
    for i in contour_centers:
        cleaned_contour_centers.append(i)
        already_removed = False
        for j in cleaned_contour_centers:
            distance = dist(i,j)
            if distance < apprx_bead_radius and distance != 0:
                if not(already_removed):
                    cleaned_contour_centers.pop()
                    already_removed = True
                    cleaned_contour_centers.remove(j)
                    cleaned_contour_centers.append([int((i[0]+j[0])/2),int((i[1]+j[1])/2)])

    # recolor image for preview
    colorMasked = cv2.cvtColor(masked_image, cv2.COLOR_GRAY2BGR)
    # drawing marker at center and circle with radius same as that of a bead 
    for i in cleaned_contour_centers:
        x_com,y_com = i
        cv2.drawMarker(colorMasked, (x_com,y_com), [0,255,0])
        cv2.circle(colorMasked, (x_com, y_com), apprx_bead_radius, (0, 200, 0), 3)
        # cv2.putText(colorMasked, str(i), (int(x), int(y)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,150,0), 2)

    # append frame in superlist containing data for all frames
    cord_list.append(np.unique(cleaned_contour_centers,axis=0))

    # displaying the video 
    cv2.imshow("Live", colorMasked)
        
    # write to gray-scale 
    result.write(cv2.cvtColor(colorMasked, cv2.COLOR_BGR2GRAY))
  
    # exiting the loop 
    key = cv2.waitKey(1) # using cv2.waitKey(0) stops the for loop, which progress only only pressing spacebar on the preview window 
    if key == ord("q"): 
        break

# close the window once all frames are processed and save the output by releasing result
cv2.destroyAllWindows() 
source.release()
result.release()

# for i in cord_list:
#     print(len(i))


# now from positions for each frames we wish to track each bead across all frames

master_array = []

# in this mtd first frame sets number of objects to be tracked - take care with contour length threshhold such that this numbe never drops below the number in first frame - otherwise this case is not handled properly

#  for each point in current frame we find the nearest point in last frame of each track in master_array, then depending on weather the nearest points distance either we add it to that track 

# here obviously we are assuming at case where travel distance per frame is far smaller compared to radius of bead  

for i in range(len(cord_list)):
    if i == 0:
        for j in cord_list[i]:
            master_array.append([j])
    else:
        # find distance from each point in prev frame to each pont in this frame
        for k in master_array:
            prev_pt = k[-1]
            dist_ = 10000 # some initial large no
            nearest_pt = []
            for pt in cord_list[i]:
                d = dist(pt,prev_pt)
                if dist_ > d:
                    dist_ = d
                    nearest_pt = pt
            if dist_ < apprx_bead_radius: # apprx radius of beads
                k.append(nearest_pt)
            else:
                k.append(k[-1])

# save the outputs
pt_array = np.array(master_array,dtype=object)
np.save("bead_tracks.npy",pt_array)

master_array = np.load('bead_tracks.npy',allow_pickle=True)
print(np.shape(master_array))

# # ###############################
# # for ploting histogram of contour lengths
# import matplotlib.pyplot as plt

# # Plotting a basic histogram
# plt.hist(size_dist, bins=30, color='skyblue', edgecolor='black')

# # Adding labels and title
# plt.xlabel('Contour Length')
# plt.ylabel('Frequency')
# plt.title('contour length distribution')

# # Display the plot
# plt.show()
