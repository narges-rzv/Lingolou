import { useEffect, useRef } from 'react';

interface Node {
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  sparkTime: number;
  sparkHop: number;
  sparkId: number;
}

interface SparkEdge {
  from: Node;
  to: Node;
  startTime: number;
  hop: number;
  sid: number;
}

interface SparkQueueEntry {
  node: Node;
  time: number;
  hop: number;
  sid: number;
}

const NODE_COUNT = 400;
const CONNECT_DIST = 70;
const CONNECT_DIST_SQ = CONNECT_DIST * CONNECT_DIST;
const SPARK_INTERVAL = 3000;
const SPARK_PROPAGATE_DELAY = 100;
const SPARK_DEGREES = 7;
const SPARK_FADE = 2200;
const EDGE_FADE = 600;

const BASE_COLOR_R = 100, BASE_COLOR_G = 90, BASE_COLOR_B = 180;
const SPARK_PALETTE: [number, number, number][] = [
  [120, 200, 255],
  [160, 140, 255],
  [255, 200, 100],
];

function heartbeatEase(t: number): number {
  if (t <= 0) return 0;
  if (t >= 1) return 1;
  return 1 - (1 - t) * (1 - t);
}

export default function ConnectionBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d')!;

    let W = 0, H = 0;
    function resize() {
      W = canvas!.width = window.innerWidth;
      H = canvas!.height = window.innerHeight;
    }
    resize();
    window.addEventListener('resize', resize);

    // Nodes
    const nodes: Node[] = [];
    for (let i = 0; i < NODE_COUNT; i++) {
      nodes.push({
        x: Math.random() * W,
        y: Math.random() * H,
        vx: (Math.random() - 0.5) * 0.5,
        vy: (Math.random() - 0.5) * 0.5,
        radius: 2 + Math.random() * 1.5,
        sparkTime: -99999,
        sparkHop: -1,
        sparkId: -1,
      });
    }

    let sparkIdCounter = 0;
    const sparkEdges: SparkEdge[] = [];
    const sparkQueue: SparkQueueEntry[] = [];
    let lastSpark = 0;

    // Pre-rendered glow
    const glowCanvas = document.createElement('canvas');
    const glowSize = 48;
    glowCanvas.width = glowSize * 2;
    glowCanvas.height = glowSize * 2;
    const glowCtx = glowCanvas.getContext('2d')!;
    const glowGrad = glowCtx.createRadialGradient(glowSize, glowSize, 0, glowSize, glowSize, glowSize);
    glowGrad.addColorStop(0, 'rgba(255,255,255,0.35)');
    glowGrad.addColorStop(0.5, 'rgba(255,255,255,0.08)');
    glowGrad.addColorStop(1, 'rgba(255,255,255,0)');
    glowCtx.fillStyle = glowGrad;
    glowCtx.fillRect(0, 0, glowSize * 2, glowSize * 2);

    function updateNode(node: Node) {
      node.x += node.vx;
      node.y += node.vy;
      if (node.x < 0) { node.x = 0; node.vx *= -1; }
      if (node.x > W) { node.x = W; node.vx *= -1; }
      if (node.y < 0) { node.y = 0; node.vy *= -1; }
      if (node.y > H) { node.y = H; node.vy *= -1; }
    }

    function sparkIntensity(node: Node, now: number): number {
      if (node.sparkHop < 0) return 0;
      const elapsed = now - node.sparkTime;
      if (elapsed < 0) return 0;
      const t = 1 - elapsed / SPARK_FADE;
      if (t <= 0) { node.sparkHop = -1; return 0; }
      return t;
    }

    function triggerSpark(now: number) {
      const origin = nodes[Math.floor(Math.random() * nodes.length)];
      const sid = sparkIdCounter++;
      origin.sparkTime = now;
      origin.sparkHop = 0;
      origin.sparkId = sid;

      const visited = new Set<Node>();
      visited.add(origin);
      let frontier: Node[] = [origin];

      for (let hop = 1; hop <= SPARK_DEGREES; hop++) {
        const nextFrontier: Node[] = [];
        for (const src of frontier) {
          for (const dst of nodes) {
            if (visited.has(dst)) continue;
            const dx = dst.x - src.x;
            const dy = dst.y - src.y;
            if (dx * dx + dy * dy < CONNECT_DIST_SQ) {
              visited.add(dst);
              const edgeStart = now + (hop - 1) * SPARK_PROPAGATE_DELAY;
              sparkEdges.push({ from: src, to: dst, startTime: edgeStart, hop, sid });
              sparkQueue.push({ node: dst, time: edgeStart + SPARK_PROPAGATE_DELAY, hop, sid });
              nextFrontier.push(dst);
            }
          }
        }
        frontier = nextFrontier;
        if (frontier.length === 0) break;
      }
    }

    function processSparkQueue(now: number) {
      let i = 0;
      while (i < sparkQueue.length) {
        const entry = sparkQueue[i];
        if (now >= entry.time) {
          if (entry.time > entry.node.sparkTime) {
            entry.node.sparkTime = entry.time;
            entry.node.sparkHop = entry.hop;
            entry.node.sparkId = entry.sid;
          }
          sparkQueue[i] = sparkQueue[sparkQueue.length - 1];
          sparkQueue.pop();
        } else {
          i++;
        }
      }
    }

    function pruneSparkEdges(now: number) {
      const totalLife = SPARK_PROPAGATE_DELAY + EDGE_FADE;
      let i = 0;
      while (i < sparkEdges.length) {
        if (now - sparkEdges[i].startTime > totalLife) {
          sparkEdges[i] = sparkEdges[sparkEdges.length - 1];
          sparkEdges.pop();
        } else {
          i++;
        }
      }
    }

    let animId: number;
    function draw(now: number) {
      processSparkQueue(now);
      if (now % 5000 < 16) pruneSparkEdges(now);

      ctx.clearRect(0, 0, W, H);

      for (const node of nodes) updateNode(node);

      const intensities = new Float32Array(NODE_COUNT);
      for (let i = 0; i < NODE_COUNT; i++) {
        intensities[i] = sparkIntensity(nodes[i], now);
      }

      // Spark edges
      for (const e of sparkEdges) {
        const elapsed = now - e.startTime;
        if (elapsed < 0) continue;
        const sc = SPARK_PALETTE[e.hop % 3];
        const fromX = e.from.x, fromY = e.from.y;
        const toX = e.to.x, toY = e.to.y;

        if (elapsed < SPARK_PROPAGATE_DELAY) {
          const rawT = elapsed / SPARK_PROPAGATE_DELAY;
          const t = heartbeatEase(rawT);
          const midX = fromX + (toX - fromX) * t;
          const midY = fromY + (toY - fromY) * t;
          const alpha = 0.6 + 0.4 * (1 - rawT);
          ctx.beginPath();
          ctx.moveTo(fromX, fromY);
          ctx.lineTo(midX, midY);
          ctx.strokeStyle = `rgba(${sc[0]},${sc[1]},${sc[2]},${alpha.toFixed(2)})`;
          ctx.lineWidth = 2.2;
          ctx.stroke();
          ctx.beginPath();
          ctx.arc(midX, midY, 2.5, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(255,255,255,${(0.7 * (1 - rawT * 0.5)).toFixed(2)})`;
          ctx.fill();
        } else {
          const fadeT = 1 - (elapsed - SPARK_PROPAGATE_DELAY) / EDGE_FADE;
          if (fadeT <= 0) continue;
          ctx.beginPath();
          ctx.moveTo(fromX, fromY);
          ctx.lineTo(toX, toY);
          ctx.strokeStyle = `rgba(${sc[0]},${sc[1]},${sc[2]},${(fadeT * 0.15).toFixed(3)})`;
          ctx.lineWidth = 0.6 + fadeT * 0.6;
          ctx.stroke();
        }
      }

      // Nodes
      for (let i = 0; i < NODE_COUNT; i++) {
        const node = nodes[i];
        const spark = intensities[i];
        let r = BASE_COLOR_R, g = BASE_COLOR_G, bl = BASE_COLOR_B;
        let alpha = 0.5;
        let rad = node.radius;

        if (spark > 0) {
          const sc = SPARK_PALETTE[node.sparkHop % 3];
          r = r + (sc[0] - r) * spark;
          g = g + (sc[1] - g) * spark;
          bl = bl + (sc[2] - bl) * spark;
          alpha = 0.5 + 0.5 * spark;
          rad = node.radius + spark * 2.5;
          const glowScale = (rad * 4) / glowSize;
          ctx.globalAlpha = spark * 0.6;
          ctx.drawImage(glowCanvas, node.x - glowSize * glowScale, node.y - glowSize * glowScale, glowSize * 2 * glowScale, glowSize * 2 * glowScale);
          ctx.globalAlpha = 1;
        }

        ctx.beginPath();
        ctx.arc(node.x, node.y, rad, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${r|0},${g|0},${bl|0},${alpha.toFixed(2)})`;
        ctx.fill();
      }

      if (now - lastSpark > SPARK_INTERVAL) {
        triggerSpark(now);
        lastSpark = now;
      }

      animId = requestAnimationFrame(draw);
    }

    animId = requestAnimationFrame(draw);

    return () => {
      window.removeEventListener('resize', resize);
      cancelAnimationFrame(animId);
    };
  }, []);

  return <canvas ref={canvasRef} className="connection-bg" />;
}
