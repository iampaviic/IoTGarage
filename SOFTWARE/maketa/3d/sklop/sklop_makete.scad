// IoT Garaža – 3D assembly of the whole physical model (all dimensions in mm).
//
// The layout is computed exactly like alati/tlocrt.py (same formulas, same defaults), so this model, the 1:1
// floor plan and the camera calculator always agree. North = +Y. Printed parts come from ../*.scad and are
// shown in orange; purchased components (komponente.scad) in their real colours.
//
//   openscad sklop_makete.scad                          # interactive preview (F5)
//   python izvoz.py                                     # PNG views + STL + coloured GLB (see README.md)
//
// Scene: a car waits at the entrance (barrier closed, red LED), a car leaves through the open exit barrier
// (green LED), two cars are parked on P02 and P05 (red spot LEDs).

include <komponente.scad>
demo = false;
use <../rampa_sg90.scad>
use <../most_kamere.scad>
use <../nosac_hcsr04.scad>
use <../nosac_ir.scad>
use <../drzac_tablice.scad>
use <../granicnik.scad>

car_scale = 24;          // 1:N model cars (same as tlocrt.py --scale)
spots = 6;               // number of parking spots (tlocrt.py --spots)
occupied = [2, 5];       // spots with a parked car
exit_open = true;        // exit barrier open, entrance closed
wall_h = 130;            // Forex walls; the sensor bridge rests on them
bridge_z = 113;          // underside of the sensor bridge (dimenzije.md: HC-SR04 113 mm above the floor)
show_walls = true;
show_cars = true;

// ------------------------------------------------------------------ layout (= tlocrt.py)
function s(metres) = round(metres * 1000 / car_scale);
m = 20;
spot_w = s(2.6); spot_d = s(5.3); aisle = s(4.8); lane_w = s(3.2); island = s(1.6);
car_len = s(4.4);
cam_behind = 200;
outside = cam_behind + 60;
inside = 100;
W = max(spots * spot_w, 2 * lane_w + island + 2 * 60) + 2 * m;
H = m + spot_d + aisle + inside + outside + m;
x0 = (W - spots * spot_w) / 2;
lanes_w = 2 * lane_w + island;
lx = (W - lanes_w) / 2;
// SVG y (down) -> Y (north up)
Y_spots0 = H - m - spot_d;                 // south edge of the spots
Y_spot_c = H - m - spot_d / 2;             // centre line of the spots (sensor bridge)
Y_lanes1 = H - m - spot_d - aisle;         // north end of the lanes = south edge of the aisle
Y_bar = H - (m + spot_d + aisle + inside); // barrier line
Y_stop_in = Y_bar - 40;                    // entering car waits outside, plate on this line
Y_stop_out = Y_bar + 40;                   // leaving car waits inside
X_in = lx + lane_w / 2;                    // entrance lane centre
X_isl = lx + lane_w;                       // island west edge
X_out = lx + lane_w + island + lane_w / 2; // exit lane centre
echo(str("baza ", W, " x ", H, " mm, mjesto ", spot_w, " x ", spot_d, ", rampa Y=", Y_bar));

function spot_x(i) = x0 + (i - 0.5) * spot_w;   // centre of spot i (1-based)

// ------------------------------------------------------------------ base, floor markings, walls
module floor_and_base() {
    dio("baza") translate([0, 0, -5]) cube([W, H, 5]);
    // asphalt: spots + aisle + both lanes
    dio("asfalt") {
        translate([m, Y_lanes1, 0]) cube([W - 2 * m, H - m - Y_lanes1, 0.4]);
        translate([lx, m, 0]) cube([lanes_w, Y_lanes1 - m, 0.4]);
    }
    dio("zelena") translate([X_isl, m, 0]) cube([island, Y_lanes1 - m, 0.6]);
    // spot separators (white) and numbers
    dio("bijela") {
        for (i = [0:spots]) translate([x0 + i * spot_w - 1.5, Y_spots0, 0]) cube([3, spot_d, 0.6]);
        for (i = [1:spots]) translate([spot_x(i), Y_spots0 + 18, 0])
            linear_extrude(0.6) text(str("P0", i), size = 16, font = font, halign = "center");
        // stop lines and lane arrows
        translate([lx + 10, Y_stop_in - 1.5, 0]) cube([lane_w - 20, 3, 0.6]);
        translate([lx + lane_w + island + 10, Y_stop_out - 1.5, 0]) cube([lane_w - 20, 3, 0.6]);
        translate([X_in, m + 4, 0]) linear_extrude(0.6) text("ULAZ", size = 13, font = font, halign = "center");
        translate([X_out, m + 4, 0]) linear_extrude(0.6) text("IZLAZ", size = 13, font = font, halign = "center");
    }
    // barrier lines (red, dashed)
    dio("crvena") for (x0l = [lx, lx + lane_w + island]) for (k = [0:5])
        translate([x0l + 4 + k * 22, Y_bar - 2.5, 0]) cube([12, 5, 0.6]);
}

module walls() {
    t = 5;
    dio("forex") {
        translate([0, H - t, 0]) cube([W, t, wall_h]);                       // north
        for (x = [0, W - t]) translate([x, Y_lanes1, 0]) cube([t, H - Y_lanes1, wall_h]);   // west / east
        // south wall with the opening for both lanes
        translate([0, Y_lanes1, 0]) cube([lx, t, wall_h]);
        translate([lx + lanes_w, Y_lanes1, 0]) cube([W - lx - lanes_w, t, wall_h]);
    }
}

// ------------------------------------------------------------------ sensor bridge over the spots
module sensor_bridge() {
    t = 5; bw = 40;
    dio("forex") difference() {
        translate([5, Y_spot_c - bw / 2, bridge_z]) cube([W - 10, bw, t]);
        for (i = [1:spots]) for (sx = [-13, 13]) translate([spot_x(i) + sx, Y_spot_c, bridge_z - 1])
            cylinder(d = 17, h = t + 2, $fn = 32);
    }
    // two Forex brackets from the north wall carry the middle of the bridge
    dio("forex") for (k = [round(spots / 3), spots - round(spots / 3)]) if (k > 0 && k < spots)
        translate([x0 + k * spot_w - 7.5, Y_spot_c, bridge_z + t]) cube([15, H - 5 - Y_spot_c, t]);
    for (i = [1:spots]) translate([spot_x(i), Y_spot_c, bridge_z + t]) {
        dio("pla") nosac_hcsr04();
        translate([0, 0, 3 + 0.1]) hc_sr04();
        // spot state LED on the front edge of the bridge, looking at the aisle
        translate([0, -bw / 2, -t / 2]) rotate([0, 0, 180])
            led_ws2812(len(search(i, occupied)) > 0 ? "led_crvena" : "led_zelena");
    }
    // sensor node ESP32 (floor plan: aisle, north-east corner)
    translate([W - m - 30, Y_spots0 - 6 - 14, 0]) esp32_devkit();
}

// ------------------------------------------------------------------ barriers, IR sensors, island electronics
module barrier(arm_dir, open) {
    // post rotated so the servo's long axis runs along the lane; the arm swings horizontally
    rotate([0, 0, 90]) {
        dio("pla") post();
        translate([0, 0, 38.5 - 15.9]) sg90();               // tabs rest on the pocket rim (post_h - tab_t)
        translate([5.5, 0, 50]) rotate([0, 0, (open ? 90 : arm_dir) - 90]) striped_arm();
    }
}

module striped_arm() {
    stripe = 16;
    // render(): the preview cannot colour a CSG intersection, a mesh it can
    dio("crvena") render() intersection() {
        arm();
        union() { translate([-10, -10, -1]) cube([10, 20, 10]); for (k = [0:2:9]) translate([k * stripe, -10, -1]) cube([stripe, 20, 10]); }
    }
    dio("bijela") render() intersection() { arm(); for (k = [1:2:9]) translate([k * stripe, -10, -1]) cube([stripe, 20, 10]); }
}

module gates() {
    post_foot = 12.4 + 4 + 16;                                   // post_w + foot (rampa_sg90.scad)
    xe = X_isl + post_foot / 2 + 0.6;                            // entrance post on the island, west half
    xx = X_isl + island - post_foot / 2 - 0.6;                   // exit post, east half
    translate([xe, Y_bar, 0]) {
        barrier(arm_dir = 180, open = false);                   // arm points west across the entrance lane
        translate([-8.2, -6, 30]) rotate([0, 0, 90]) led5("led_crvena");
        translate([-8.2, 6, 30]) rotate([0, 0, 90]) led5("crna");
    }
    translate([xx, Y_bar, 0]) {
        barrier(arm_dir = 0, open = exit_open);
        translate([8.2, -6, 30]) rotate([0, 0, -90]) led5(exit_open ? "crna" : "led_crvena");
        translate([8.2, 6, 30]) rotate([0, 0, -90]) led5(exit_open ? "led_zelena" : "crna");
    }
    // IR sensors at the barrier line, on the side opposite the post, looking across the lane
    translate([lx + 12, Y_bar, 0]) { dio("pla") nosac_ir(); fc51(); }
    translate([lx + lanes_w - 12, Y_bar, 0]) rotate([0, 0, 180]) { dio("pla") nosac_ir(); fc51(); }
    // gate node ESP32 + manual buttons on the island, south of the posts
    translate([X_isl + island / 2, Y_bar - 95, 0]) rotate([0, 0, 90]) esp32_devkit();
    translate([X_isl + 18, Y_bar - 140, 0]) tipkalo("crvena");
    translate([X_isl + island - 18, Y_bar - 140, 0]) tipkalo("zelena");
    // wheel stops: the waiting car's plate ends up on the stop line
    // (car front = plate on the stop line; front wheel 32 mm behind the bumper, r = 13.5)
    translate([X_in - 55, Y_stop_in - 2.2 - 32 + 13.5 + 0.5, 0]) dio("pla") granicnik();
    translate([X_out - 55, Y_stop_out + 2.2 + 32 - 13.5 - 0.5 - 10, 0]) dio("pla") granicnik();
}

// ------------------------------------------------------------------ camera bridges (two cameras, variant A)
// most_kamere.scad: legs 110 + crossbar 6, hinge axis 6 above the bar = 122 mm. The plate hangs upside down on
// the hinge, the webcam is strapped on it 15 mm in front of the axis. The tilt is computed so the lens looks at
// the centre of the waiting car's plate; echo prints the numbers to compare with alati/kamera_kalkulator.py.
cam_leg = 10; cam_leg_h = 110; cam_axis = cam_leg_h + 6 + 6;
plate_z = 12 + 1.5 + 13.2 / 2;             // plate centre on the toy car (autic: bumper 12, frame 1.5)
function lens_up(t) = -25 * sin(t) + 19 * cos(t);       // lens centre relative to the hinge axis, tilt t
function lens_ahead(t) = 25 * cos(t) + 19 * sin(t);
function aim(t) = atan((cam_axis + lens_up(t) - plate_z) / (cam_behind + 40));   // plate 40 mm past the barrier
cam_tilt = aim(aim(aim(25)));
cam_lens_z = cam_axis + lens_up(cam_tilt);
echo(str("kamera: objektiv ", round(cam_lens_z), " mm iznad poda, ", cam_behind, " mm iza crte rampe, nagib ",
         round(cam_tilt * 10) / 10, " st. (kamera_kalkulator.py --cam-behind ", cam_behind, " --cam-height ",
         round(cam_lens_z), " --plate-height ", round(plate_z), ")"));

module camera_bridge() {
    span = lane_w + 2 * cam_leg + 10;
    // local frame: the camera looks +Y, the bar is placed so the LENS (not the bar) is cam_behind from the barrier
    translate([0, -lens_ahead(cam_tilt), 0]) {
        translate([-span / 2, -cam_leg / 2, 0]) dio("pla") {
            leg(); translate([span - cam_leg, 0, 0]) leg(); translate([0, 0, cam_leg_h]) bar();
        }
        translate([0, 0, cam_axis]) rotate([-cam_tilt, 0, 0]) {
            dio("pla") translate([-25, -3, 8]) mirror([0, 0, 1]) plate();       // lugs down, around the hinge block
            dio("srebrna") translate([-10, 0, 0]) rotate([0, 90, 0]) cylinder(d = 3, h = 20, $fn = 12);   // M3 hinge
            translate([0, 15, 8]) usb_kamera();
        }
    }
}

// eye (lens) and a point 300 mm along the view direction, for the "what the camera sees" render in izvoz.py
function cam_view(origin, look) = let(d = [0, look * cos(cam_tilt), -sin(cam_tilt)], e = origin + [0, 0, cam_lens_z])
    [e + 4 * d, e + 300 * d];
echo(kamera_ulaz = cam_view([X_in, Y_bar + cam_behind, 0], -1));
echo(kamera_izlaz = cam_view([X_out, Y_bar - cam_behind, 0], 1));

module cameras() {
    translate([X_in, Y_bar + cam_behind, 0]) rotate([0, 0, 180]) camera_bridge();   // entrance: looks south
    translate([X_out, Y_bar - cam_behind, 0]) camera_bridge();                      // exit: looks north
}

// ------------------------------------------------------------------ edge computer and power (outside corners)
module electronics() {
    translate([W - m - 95, m + 10, 0]) raspberry_pi();
    translate([m + 5, m + 10, 0]) napajanje();
}

// ------------------------------------------------------------------ cars
module cars() {
    translate([X_in, Y_stop_in - car_len / 2 - 2.2, 0]) rotate([0, 0, 90]) autic("auto_crveni", "ZG 1234-AB");
    translate([X_out, Y_stop_out + car_len / 2 + 2.2, 0]) rotate([0, 0, -90]) autic("auto_plavi", "RI 507-TK");
    colours = ["auto_zuti", "auto_srebrni", "auto_crveni", "auto_plavi"];
    plates = ["ST 2468-KM", "OS 135-PP", "PU 88-DA", "ZD 4040-LV"];
    for (k = [0:len(occupied) - 1]) translate([spot_x(occupied[k]), Y_spot_c - 6, 0]) rotate([0, 0, 90])
        autic(colours[k % 4], plates[k % 4]);
}

// ------------------------------------------------------------------ the whole model
module garage() {
    floor_and_base();
    if (show_walls) walls();
    sensor_bridge();
    gates();
    cameras();
    electronics();
    if (show_cars) cars();
}

garage();
