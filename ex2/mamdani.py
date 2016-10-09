

def fuzzy_and(v1, v2):
    return min(v1,v2)

def fuzzy_or(v1, v2):
    return max(v1,v2)

def fuzzy_not(x):
    return 1-x

def triangle(pos, x0, x1,clip=None):
    # x0, x1, x2 is left, center and right of triangle, respectively
    value = 0
    center = (x0+x1)/2
    if pos >= x0 and pos <= center:
        value = (pos-x0)/(center-x0)
    elif pos >= center and pos <= x1:
        value = (x1-pos)/(center-x0)
    if clip is not None and value > clip:
        value = clip
    return value

def grade(pos, x0, x1, clip=None):
    value = 0
    if pos >= x1:
        value = 1
    elif pos <= x0:
        value = 0
    else:
        value = (pos-x0)/(x1-x0)
    if clip is not None and value > clip:
        value = clip
    return value


def reverse_grade(pos, x0, x1, clip=None):
    value = 0
    if pos <= x0:
        value = 1
    elif pos >= x0:
        value = 0
    else:
        value = (x1-pos)/(x1-x0)
    if clip is not None and value> clip:
        value = clip
    return value

def membership(x, mode, triangles, grades):
    if mode in triangles.keys():
        x0, x1 = triangles[mode]
        return triangle(x, x0, x1)
    else:
        # We have two grade at both "edges"
        # The smallest of them is the reverse grade, and the second is grade
        x0, x1 = grades[mode]

        if (x0,x1) == min(grades.values()):
            return reverse_grade(x, x0, x1)
        else:
            return grade(x, x0, x1)

def distance_membership(distance, mode):
    distance_triangles = {"small": (1.5, 4.5), "perfect": (3.5, 6.5), "big": (5.5, 8.5)}
    distance_grades = {"very_small": (1, 2.5), "very_big": (7.5, 9)}
    return membership(distance, mode, distance_triangles, distance_grades)

def delta_membership(delta, mode):
    delta_triangles = {"shrinking":(-3.5, -0.5), "stable": (-1.5, 1.5), "growing": (0.5, 3.5)}
    delta_grades = {"shrinking_fast": (-5, -2.5), "growing_fast": (2.5, 5)}
    return membership(delta, mode, delta_triangles, delta_grades)

def action_membership(value, mode=None):
    action_triangles = {"slowdown": (-7, -1), "none": (-3, 3), "speedup": (1, 7)}
    action_grades = {"brakehard": (-8, -5), "floorit": (5, 8)}
    # Go through each mode, and find out the membership of the value
    membership_values = {}
    if mode is not None:
        return membership(value, mode, action_triangles, action_grades)

    for mode in action_triangles.keys():
        membership_values[mode] = membership(value, mode, action_triangles, action_grades)
    for mode in action_grades.keys():
        membership_values[mode] = membership(value, mode, action_triangles, action_grades)
    return membership_values



def aggregate_results(results):
    action_triangles = {"slowdown": (-7, -1), "none": (-3, 3), "speedup": (1, 7)}
    action_grades = {"brakehard": (-8, -5), "floorit": (5, 8)}
    # This will be our return data.
    data = []
    # Merge the two dictionaries, so that we can easily iterate through them
    shapes = {**action_triangles, **action_grades}
    for v in range(-10,11):
        value = 0

        for mode, value_range in zip(shapes.keys(), shapes.values()):
            if mode in results.keys():
                start, end = value_range
                if mode in action_triangles.keys():
                    current = triangle(v, start, end, clip=results[mode])
                elif mode == "brakehard":
                    current = reverse_grade(v, start, end, clip=results[mode])
                elif mode == "floorit":
                    current = grade(v, start, end, clip=results[mode])
                # If multiple values in an area, choose the biggest
                if current > value:
                    value = current

        data.append(value)
    # Remove all zeroes, we dont need them to calculate COG
    return data

def cog(data):
    # Returns senter of gravity
    # Note, the increments are hard-coded to be 1. This should be changed
    # to increase accuracy.
    try:
        return sum(x*y for x,y in zip(data, range(-10,11)))/sum(data)
    except ZeroDivisionError:
        return sum(x*y for x,y in zip(data, range(-10,11)))

def rules(distance, delta):
    # IF	distance	is	Small	AND	delta	is	Growing	THEN	action	is	None
    action_none = fuzzy_and( distance_membership(distance, "small"), delta_membership(delta, "growing"))
    # IF	distance	is	Small	AND	delta	is	Stable	THEN	action	is	SlowDown
    action_slowdown = fuzzy_and( distance_membership(distance, "small"), delta_membership(delta, "stable"))
    # IF	distance	is	Perfect	AND	delta	is	Growing	THEN	action	is	SpeedUp
    action_speedup = fuzzy_and( distance_membership(distance, "perfect"), delta_membership(delta, "growing"))
    #IF	distance is	VeryBig	AND	(delta	is	NOT	Growing	OR	delta	is	NOT	GrowingFast) THEN action is	FloorIt
    # Split the statement for readability
    partial_statement = fuzzy_or( fuzzy_not(delta_membership(delta, "growing")), fuzzy_not(delta_membership(delta, "growing_fast")))
    action_floorit = fuzzy_and( distance_membership(distance, "very_big"), partial_statement)
    # IF	distance	is	VerySmall	THEN	action	is	BrakeHard
    action_brakehard = distance_membership(distance, "very_small")

    results = [action_none, action_slowdown, action_speedup, action_floorit, action_brakehard]
    return results

def print_debug_info(action_weights, data, COG, action_membership_list, decision):
    print(action_weights)
    print("="*20)
    print("DATA: ", data)
    print("="*20)
    print("COG:", COG)
    print(action_membership_list)
    print("DECISION MADE: ", decision)

def make_decision(distance, delta, debug=False):
    modes = ["none", "slowdown", "speedup", "floorit", "brakehard"]
    # Stores values for each possible action, remove all that are zeroes
    # We dont need them to calculate anything
    results = rules(distance, delta)
    action_weights = {}

    for mode, action_weight in zip(modes, results):
        if action_weight != 0:
            action_weights[mode] = action_weight

    data = aggregate_results(action_weights)
    COG = cog(data)
    #Find out which action has the maximum value in COG
    action_membership_list = action_membership(COG)

    decision = max(action_membership_list, key=action_membership_list.get)

    if debug:
        print_debug_info(action_weights, data, COG, action_membership_list, decision)

    return decision

if __name__ == "__main__":
    dst = float(input("Distance: "))
    delta = float(input("Delta: "))
    decision = make_decision(dst, delta)
    print("Made decision:", decision)
