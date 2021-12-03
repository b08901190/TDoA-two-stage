# -*- coding: utf-8 -*-
"""「brand_new_demo.ipynb」的副本

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1XwngZiTZIIRwv4wwexajPnohSbNvdJ0P
"""

import numpy as np
from scipy import optimize
import sys, collections, time
from scipy.optimize import lsq_linear, root, minimize
import random
import matplotlib.pyplot as plt
from tqdm import tqdm, trange
import numpy.matlib 
from itertools import product
from itertools import combinations
from collections import Counter
import numpy as np
import matplotlib.pyplot as plt 
from mpl_toolkits.mplot3d import Axes3D
import heapq
import random

def lsq_method(distances_to_anchors, anchor_positions): ##x 和 y 軸是準的 ，z軸在共平面時又大誤差
    distances_to_anchors, anchor_positions = np.array(distances_to_anchors), np.array(anchor_positions)
    if not np.all(distances_to_anchors):
        raise ValueError('Bad uwb connection. distances_to_anchors must never be zero. ' + str(distances_to_anchors))
    anchor_offset = anchor_positions[0]
    anchor_positions = anchor_positions[1:] - anchor_offset
    K = np.sum(np.square(anchor_positions), axis=1)   #ax=1 列加
    squared_distances_to_anchors = np.square(distances_to_anchors)
    squared_distances_to_anchors = (squared_distances_to_anchors - squared_distances_to_anchors[0])[1:]
    b = (K - squared_distances_to_anchors) / 2.
    res = lsq_linear(anchor_positions, b, lsmr_tol='auto', verbose=0)
    return res.x + anchor_offset

def costfun_method(distances_to_anchors, anchor_positions): ##找較準確的z 
    distances_to_anchors, anchor_positions = np.array(distances_to_anchors), np.array(anchor_positions)
    tag_pos = lsq_method(distances_to_anchors, anchor_positions)
    anc_z_ls_mean = np.mean(np.array([i[2] for i in anchor_positions]) )  
    new_z = (np.array([i[2] for i in anchor_positions]) - anc_z_ls_mean).reshape(5, 1)
    new_anc_pos = np.concatenate((np.delete(anchor_positions, 2, axis = 1), new_z ), axis=1)
    new_disto_anc = np.sqrt(abs(distances_to_anchors[:]**2 - (tag_pos[0] - new_anc_pos[:,0])**2 - (tag_pos[1] - new_anc_pos[:,1])**2))
    new_z = new_z.reshape(5,)

    a = (np.sum(new_disto_anc[:]**2) - 3*np.sum(new_z[:]**2))/len(anchor_positions)
    b = (np.sum((new_disto_anc[:]**2) * (new_z[:])) - np.sum(new_z[:]**3))/len(anchor_positions)
    cost = lambda z: np.sum(((z - new_z[:])**4 - 2*(((new_disto_anc[:])*(z - new_z[:]))**2 ) + new_disto_anc[:]**4))/len(anchor_positions) 

    function = lambda z: z**3 - a*z + b
    derivative = lambda z: 3*z**2 - a

    def newton(function, derivative, x0, tolerance, number_of_max_iterations=50):
        x1, k = 0, 1
        if (abs(x0-x1)<= tolerance and abs((x0-x1)/x0)<= tolerance):  return x0
        while(k <= number_of_max_iterations):
            x1 = x0 - (function(x0)/derivative(x0))
            if (abs(x0-x1)<= tolerance and abs((x0-x1)/x0)<= tolerance): return x1
            x0 = x1
            k = k + 1
            if (k > number_of_max_iterations): pass
                # print("ERROR: Exceeded max number of iterations")
        return x1 

    
    ranges = (slice(0, 100, 0.05), )
    resbrute = optimize.brute(cost, ranges, full_output = True, finish = optimize.fmin)
    new_tag_pos = np.concatenate((np.delete(np.array(tag_pos), 2), resbrute[0] + anc_z_ls_mean))
    
    return np.around(new_tag_pos, 4)

def TDoA(distances_diffrences, anchor_num, anchor_positions):
    # ((2, 1, 0), (2, 1, 3), (3, 0, 1),(3,0,2),(2,3,0),(2,3,1),(2,0,1),(2,0,3),(1,3,0),(1,3,2),(1,0,2),(1,0,3))
    target =((4, 1, 0), (3, 1, 0), (2, 1, 0),(0,3,4),(1,3,4),(2,3,4))
    X = [0]*len(target)
    Y = [0]*len(target)
    Z = [0]*len(target)

    x = [0]*anchor_num
    y = [0]*anchor_num
    z = [0]*anchor_num

    r = [0]*anchor_num
    for i in range(anchor_num):
        r[i] = anchor_positions[i][0]**2 + \
            anchor_positions[i][1]**2+anchor_positions[i][2]**2
    for i in range(anchor_num):
        x[i] = anchor_positions[i][0]
        y[i] = anchor_positions[i][1]
        z[i] = anchor_positions[i][2]
    k = 0
    N = [0]*len(target)
    for i in target:
        N[k] = (r[i[0]]-r[i[2]])/distances_diffrences[i[0]][i[2]]-(r[i[1]]-r[i[2]]) / \
            distances_diffrences[i[1]][i[2]] - \
            distances_diffrences[i[0]][i[2]]+distances_diffrences[i[1]][i[2]]
        X[k] = 2*(x[i[0]]-x[i[2]])/distances_diffrences[i[0]][i[2]] - \
            2*(x[i[1]]-x[i[2]])/distances_diffrences[i[1]][i[2]]
        Y[k] = 2*(y[i[0]]-y[i[2]])/distances_diffrences[i[0]][i[2]] - \
            2*(y[i[1]]-y[i[2]])/distances_diffrences[i[1]][i[2]]
        Z[k] = 2*(z[i[0]]-z[i[2]])/distances_diffrences[i[0]][i[2]] - \
            2*(z[i[1]]-z[i[2]])/distances_diffrences[i[1]][i[2]]
        k = k+1
    M = [[0]*3]*len(target)

    for i in range(len(target)):
        M[i] = [X[i], Y[i], Z[i]]


    Minv = np.linalg.pinv(M)

    Minv_M = np.dot(Minv, M)

    T = np.dot(Minv, N)

    x = float(T[0])
    y = float(T[1])
    z = float(T[2])
    location = [x, y, z]

    return location

def select_real_location() :
        a,b = 0,1
        x = 10 * random.uniform(a,b)
        y = 10 * random.uniform(a,b)
        z = 10 * random.uniform(a,b)
        return [x,y,z]

def calculate_distances(anchor,anchor_num,real_position):        
        distances = [0]*anchor_num
        for i in range(anchor_num):
            distance_square = 0
            for j in range(3):
                distance_square += (anchor[i][j]-real_position[j])**2
            distances[i] = distance_square **(1/2)
        return distances
def calculate_distances_diffrences(distances_to_anchors, anchor_num):
    dif = [[0 for _ in range(anchor_num)]for _ in range(anchor_num)]
    for i in range(anchor_num):
        for j in range(anchor_num):
            dif[i][j] = distances_to_anchors[i]-distances_to_anchors[j]
    return dif

# def generate_noises(anchor_num,size,noise_scale):
#     noises = [[0 for _ in range(anchor_num)]for _ in range(anchor_num)]
#     for i in range(anchor_num):
#         for j in range(i):
#             noises[i][j] = np.random.normal(loc=0, scale=noise_scale, size=size)
#             noises[j][i] = -noises[i][j]
#     return noises

all_task_positions_1m = []
for k in range(11):
    z = k
    for i in range(1,20):
        x = i*0.5
        for j in range(1,20):
            y = j*0.5

            all_task_positions_1m.append([x,y,z])
print(len(all_task_positions_1m))

def test (anchor_num ,anchor ,size ,method ,noise_scale,position_type, position=[0,0,0], with_noises=True):

#     progress = tqdm(total=size) 

    if method == "ToA":  
        progress = tqdm(total=size) 
    
    locations = [0]*size
    real_positions = [0]*size

    average_error = 0
    error_x = [0]*size
    error_y = [0]*size
    error_z = [0]*size
    error_distance = [0]*size

    noisy_distances = [0]*anchor_num
    noises = generate_noises(anchor_num,size,noise_scale)
    
    
    for k in range(size):

#         progress.update(1)
        
        if position_type == "only_one":
            [x,y,z] = position
            real_position = [x,y,z]
        
        if position_type == "select":
            [x,y,z] = select_real_location()
            real_position = [x,y,z]
        
        if position_type == "1m":
#             size = 1331
            real_position = all_task_positions_1m[k]
         
        real_positions[k]=real_position
    
        distances_to_anchors = calculate_distances(anchor,anchor_num,real_position)
        
        distances_diffrences = calculate_distances_diffrences(distances_to_anchors,anchor_num)
            
        anchor_positions = anchor

        
        if method == "ToA":
            progress.update(1)
            for i in range(anchor_num):
                noisy_distances[i] = distances_to_anchors[i] + noises[i][k]

            locations[k] = costfun_method(noisy_distances, anchor_positions)
        
        if method == "TDoA":
            
            noisy_distances_diffrences = distances_diffrences
            
            for i in range(anchor_num):
                for j in range(anchor_num):
                    if with_noises == True:
                        noisy_distances_diffrences[i][j] = distances_diffrences[i][j] + random.gauss(0,noise_scale)
            
            locations[k] = TDoA(noisy_distances_diffrences, anchor_num, anchor_positions)

        error_x[k] = (locations[k][0]-real_position[0])
        error_y[k] = (locations[k][1]-real_position[1])
        error_z[k] = (locations[k][2]-real_position[2])
        error_distance[k] = ( error_x[k]**2 + error_y[k]**2 + error_z[k]**2 )**(1/2)
        
        average_error += error_distance[k]/size
    
    return {"average_error":average_error , "error_distance":error_distance , "error_x":error_x , "error_y":error_y , "error_z":error_z , 
            "calculate_positions":locations,"real_positions":real_positions}

anchor_num = 5
anchor =[[0, 0, 0], [10, 0, 10], [0, 10, 10], [10, 10, 0],[5,5,10]]
noise_scale = 0.1
size = len(all_task_positions_1m)
method = "TDoA"
position_type = "1m"
result = test(anchor_num ,anchor ,size ,method ,noise_scale,position_type,with_noises=True)
print(result["calculate_positions"][100])
print(result["real_positions"][100])
print(result["error_distance"][100])
print(result["error_x"][100])
print(result["error_y"][100])
print(result["error_z"][100])

anchor_num = 5
anchor =[[0, 0, 0], [10, 0, 10], [0, 10, 10], [10, 10, 0],[5,5,0]]
noise_scale = 0
size = 1
method = "TDoA"
position_type = "select"
result = test(anchor_num ,anchor ,size ,method ,noise_scale,position_type,with_noises=True)
print(result["calculate_positions"])
print(result["real_positions"])
print(result["error_distance"])
print(result["error_x"])
print(result["error_y"])
print(result["error_z"])

diffrent_height_error_wo_z = [[]]*11
total_average_error_wo_z = 0
num_of_same_height = int(len(all_task_positions_1m)/11)
for i in range(11):
    x = 0
    for j in range( num_of_same_height*i,num_of_same_height*(i+1) ):
        x += ( ( result["error_x"][j]**2 + result["error_y"][j]**2 )** 0.5 ) /num_of_same_height
    diffrent_height_error_wo_z[i] = x
    
total_average_error_wo_z = sum(diffrent_height_error_wo_z)/11

print(diffrent_height_error_wo_z)
print(total_average_error_wo_z)

diffrent_height_error_w_z = [[]]*11
total_average_error_w_z = 0
num_of_same_height = int(len(all_task_positions_1m)/11)
for i in range(11):
    x = 0
    for j in range(num_of_same_height*i,num_of_same_height*(i+1)):
        x += (result["error_distance"][j]) /num_of_same_height
    diffrent_height_error_w_z[i] = x

total_average_error_w_z = sum(diffrent_height_error_w_z)/11
print(diffrent_height_error_w_z )
print(total_average_error_w_z)

#算準一點的z
anchor_num = 5
anchor =[[0, 0, 0], [10, 0, 10], [0, 10, 10], [5, 5, 0], [10, 10, 0]]
new_cal_positions = []
a = tqdm(total = size)
for i in range(size):
  real_position = result["real_positions"][i]
  calculate_position = result["calculate_positions"][i]
  distances = calculate_distances(anchor,anchor_num,real_position)      
  E = calculate_distances_diffrences(distances,anchor_num)
  A = anchor_num*[0]
  B = anchor_num*[0]
  C = anchor_num*[0]
  D = anchor_num*[0]
  for i in range(len(A)):
      A[i] = (anchor[i][0]-calculate_position[0])**2+(anchor[i][1]-calculate_position[1])**2
      B[i] = (anchor[0][0]-calculate_position[0])**2+(anchor[0][1]-calculate_position[1])**2
      C[i] = anchor[i][2]
      D[i] = anchor[0][2]
  cost = lambda z: abs(E[4][0]-((A[4]+(C[4]-z)**2)**0.5)+((B[4]+(D[4]-z)**2)**0.5)) + abs(E[1][0]-((A[1]+(C[1]-z)**2)**0.5)+((B[1]+(D[1]-z)**2)**0.5)) + abs(E[2][0]-((A[2]+(C[2]-z)**2)**0.5)+((B[2]+(D[2]-z)**2)**0.5))+abs(E[3][0]-((A[3]+(C[3]-z)**2)**0.5)+((B[3]+(D[3]-z)**2)**0.5))
  ranges = (slice(0, 10, 0.01), )
  resbrute = optimize.brute(cost, ranges, full_output = True, finish = optimize.fmin)
  if resbrute[0] > 10 or resbrute[0] < 0 :
      resbrute = optimize.brute(cost, ranges, full_output = True, finish = None)
  new_cal_position = [calculate_position[0],calculate_position[1],float(resbrute[0])]
  new_cal_positions.append(new_cal_position)
  a.update(1)
for i in range(len(new_cal_positions)):
    for j in range(3):
        if np.isnan(new_cal_positions[i][j]):
           new_cal_positions[i][j] = 0   
print(len(new_cal_positions))

new_error_xyz = [0]*len(new_cal_positions)
new_error_x = [0]*len(new_cal_positions)
new_error_y = [0]*len(new_cal_positions)
new_error_z = [0]*len(new_cal_positions)
for i in range(len(new_cal_positions)):
    new_error_x[i] = (new_cal_positions[i][0]-result["real_positions"][i][0])
    new_error_y[i] = (new_cal_positions[i][1]-result["real_positions"][i][1])
    new_error_z[i] = (new_cal_positions[i][2]-result["real_positions"][i][2])
    new_error_xyz[i] = ( new_error_x[i]**2 + new_error_y[i]**2 + new_error_z[i]**2 )**(0.5)


average_error = sum(new_error_xyz)/len(new_error_xyz)

error_sort = sorted(new_error_xyz)
average_95error = sum(error_sort[100:3871])/len(error_sort[100:3871])

print(average_error)
print(average_95error)