import * as THREE from "./vendor/three.module.min.js";

const canvas = document.getElementById("song-canvas");

if (canvas) {
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const mobile = window.innerWidth < 700;
  const renderer = new THREE.WebGLRenderer({
    canvas,
    alpha: true,
    antialias: !mobile,
    powerPreference: "low-power",
  });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, mobile ? 1.25 : 1.6));
  renderer.setClearColor(0x000000, 0);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(46, 1, 0.1, 100);
  camera.position.set(0, 3.4, 7.4);
  camera.lookAt(0, 0, 0);

  const group = new THREE.Group();
  group.rotation.x = -0.16;
  scene.add(group);

  const columns = mobile ? 52 : 82;
  const rows = mobile ? 26 : 40;
  const total = columns * rows;
  const positions = new Float32Array(total * 3);
  const colors = new Float32Array(total * 3);

  const green = new THREE.Color(0x0f6b4f);
  const pale = new THREE.Color(0x6fae92);
  const ochre = new THREE.Color(0xc98a3e);
  const color = new THREE.Color();

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));

  const material = new THREE.PointsMaterial({
    size: mobile ? 0.045 : 0.038,
    vertexColors: true,
    transparent: true,
    opacity: 0.9,
    sizeAttenuation: true,
  });

  const points = new THREE.Points(geometry, material);
  group.add(points);

  const resize = () => {
    const rect = canvas.getBoundingClientRect();
    const width = Math.max(1, rect.width);
    const height = Math.max(1, rect.height);
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  };
  new ResizeObserver(resize).observe(canvas);
  resize();

  let targetX = 0;
  let targetY = 0;
  window.addEventListener(
    "pointermove",
    (event) => {
      targetX = event.clientX / window.innerWidth - 0.5;
      targetY = event.clientY / window.innerHeight - 0.5;
    },
    { passive: true }
  );

  let visible = true;
  new IntersectionObserver(
    (entries) => {
      visible = entries[0]?.isIntersecting ?? true;
    },
    { threshold: 0.05 }
  ).observe(canvas);

  const clock = new THREE.Clock();

  const draw = () => {
    const time = clock.getElapsedTime();
    group.rotation.y += (targetX * 0.32 - group.rotation.y) * 0.035;
    group.rotation.x += (-0.16 - targetY * 0.16 - group.rotation.x) * 0.035;

    if (visible) {
      let index = 0;
      for (let row = 0; row < rows; row += 1) {
        const z = (row / (rows - 1) - 0.5) * 7.2;
        for (let column = 0; column < columns; column += 1) {
          const x = (column / (columns - 1) - 0.5) * 12.4;
          const wave =
            Math.sin(x * 0.85 + time * 0.75) * 0.46 +
            Math.cos(z * 1.05 + time * 0.52) * 0.34 +
            Math.sin((x + z) * 0.55 + time * 0.4) * 0.2;
          positions[index * 3] = x;
          positions[index * 3 + 1] = wave;
          positions[index * 3 + 2] = z;

          const height = THREE.MathUtils.clamp((wave + 1) / 2, 0, 1);
          if (height < 0.55) {
            color.copy(green).lerp(pale, height / 0.55);
          } else {
            color.copy(pale).lerp(ochre, (height - 0.55) / 0.45);
          }
          colors[index * 3] = color.r;
          colors[index * 3 + 1] = color.g;
          colors[index * 3 + 2] = color.b;
          index += 1;
        }
      }
      geometry.attributes.position.needsUpdate = true;
      geometry.attributes.color.needsUpdate = true;
      renderer.render(scene, camera);
    }

    if (!reduce) requestAnimationFrame(draw);
  };

  draw();
}
