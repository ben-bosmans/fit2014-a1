BEGIN {
  firstClause = 1;
}

#------------------------------------------------------------
# Helper functions (do not remove)
#------------------------------------------------------------
function varName(i, t, r, c) {
  return "a" i "t" t "r" r "c" c;
}

function emitClause(cl) {
  if (firstClause == 0) {
    printf(" & ");
  }
  printf("(%s)", cl);
  firstClause = 0;
}

function agentId(sym) {
  return index("ABCDEFGHIJKLMNOPQRSTUVWXYZ", sym);
}

function isFree(r, c) {
  return (cell[r,c] != "#");
}

# Variable legend:
# N,M,T     : grid rows, columns, and time horizon
# K         : maximum agent id seen in input (A->1, B->2, ...)
# i,j       : agent ids
# t         : time index
# r,c       : row and column of a cell
# sr/sc     : start row/col for agent i
# gr/gc     : goal row/col for agent i
# cell[r,c] : grid symbol at (r,c), e.g., # . A a
# clause    : text of one disjunction before emitClause(clause)

#------------------------------------------------------------
# One line gives N, M, T in any position of the file.
# Write a pattern-action statement for that here.
#------------------------------------------------------------
####

#------------------------------------------------------------
# Match a valid cell line:
# row_index col_index separator symbol
# where separator is any non-empty combination of - and :
#------------------------------------------------------------
#### {
  # Normalize whitespace, then parse:
  # f[1]=row, f[2]=col, f[3]=separator, f[4]=symbol.
  line = $0;
  gsub(/[[:space:]]+/, " ", line);
  sub(/^ /, "", line);
  sub(/ $/, "", line);

  split(line, f, / /);
  r = f[1] + 0;
  c = f[2] + 0;
  sep = f[3];
  s = f[4];

  if (sep !~ /^[-:]+$/) next;

  cell[r,c] = s;

  if (s ~ /[A-Z]/) {
    i = agentId(s);
    sr[i] = r; sc[i] = c;
    if (i > K) K = i;
  }

  if (s ~ /[a-z]/) {
    i = agentId(toupper(s));
    gr[i] = r; gc[i] = c;
    if (i > K) K = i;
  }
}

END {
  #----------------------------------------------------------
  # (1) Start and goal clauses
  #----------------------------------------------------------
  for (i = 1; i <= K; i++) {
    emitClause(varName(i, 0, sr[i], sc[i]));
    emitClause(varName(i, T, gr[i], gc[i]));
  }

  #----------------------------------------------------------
  # (2) Every agent occupies at least one free cell at each t
  #----------------------------------------------------------
  for (i = 1; i <= K; i++) {
    for (t = 0; t <= T; t++) {
      clause = "";
      for (r = 1; r <= N; r++) {
        for (c = 1; c <= M; c++) {
          if (isFree(r, c)) {
            if (clause != "") clause = clause " | ";
            clause = clause varName(i, t, r, c);
          }
        }
      }
      emitClause(clause);
    }
  }

  #----------------------------------------------------------
  # (3) Every agent occupies at most one free cell at each t
  # r1,c1 and r2,c2 iterate over two distinct free cells.
  # cStart skips duplicates and avoids pairing a cell with itself.
  #----------------------------------------------------------
  for (i = 1; i <= K; i++) {
    for (t = 0; t <= T; t++) {
      for (r1 = 1; r1 <= N; r1++) {
        for (c1 = 1; c1 <= M; c1++) {
          if (!isFree(r1, c1)) continue;
          for (r2 = r1; r2 <= N; r2++) {
            cStart = (r2 == r1 ? c1 + 1 : 1);
            for (c2 = cStart; c2 <= M; c2++) {
              if (!isFree(r2, c2)) continue;
              emitClause("~" varName(i, t, r1, c1) " | ~" varName(i, t, r2, c2));
            }
          }
        }
      }
    }
  }

  #----------------------------------------------------------
  # (4) Trap avoidance for all agents and times
  # Complete the marked line only, which is supposed to emit
  # a clause forbidding an agent from occupying a trap cell
  # at any time step.
  #----------------------------------------------------------
  for (i = 1; i <= K; i++) {
    for (t = 0; t <= T; t++) {
      for (r = 1; r <= N; r++) {
        for (c = 1; c <= M; c++) {
          if (cell[r,c] == "#") {
            ####
          }
        }
      }
    }
  }

  #----------------------------------------------------------
  # (5) Legal movement from time t to t+1
  #----------------------------------------------------------
  for (i = 1; i <= K; i++) {
    for (t = 0; t < T; t++) {
      for (r = 1; r <= N; r++) {
        for (c = 1; c <= M; c++) {
          if (!isFree(r, c)) continue;

          clause = "~" varName(i, t, r, c) " | " varName(i, t+1, r, c);

          if (r > 1 && isFree(r-1, c)) clause = clause " | " varName(i, t+1, r-1, c);
          if (r < N && isFree(r+1, c)) clause = clause " | " varName(i, t+1, r+1, c);
          if (c > 1 && isFree(r, c-1)) clause = clause " | " varName(i, t+1, r, c-1);
          if (c < M && isFree(r, c+1)) clause = clause " | " varName(i, t+1, r, c+1);

          emitClause(clause);
        }
      }
    }
  }

  #----------------------------------------------------------
  # (6) No co-location: two different agents cannot share a cell
  # Complete the marked line only. It is supposed to emit a
  # clause forbidding two agents from occupying the same cell
  # simultaneously.
  #----------------------------------------------------------
  for (t = 0; t <= T; t++) {
    for (r = 1; r <= N; r++) {
      for (c = 1; c <= M; c++) {
        if (!isFree(r, c)) continue;
        for (i = 1; i <= K-1; i++) {
          for (j = i+1; j <= K; j++) {
            ####
          }
        }
      }
    }
  }

  printf("\n");
}
