#pragma OPENCL EXTENSION cl_khr_fp64 : enable 

double maxi(double a, double b){
    if (a<=b){
       return b;
    }
    else
    {
       return a;
    }
}


double mini(double a, double b){
    if (a<=b){
       return a;
    }
    else
    {
       return b;
    }
}

void runoffadd(__global double *bigwater, __global double *bigdem, int centerrow, 
               int centercol, const double missingvalue, const int numrows) {
    int rowloc, colloc;
    double ht_diff, center_water_elev, cell_water_elev, flow;   

      for (rowloc=centerrow-1; rowloc<=centerrow+1; rowloc++)
      {    
	  for (colloc=centercol-1; colloc<=centercol+1; colloc++)
	  { 
	      // make sure centre element is not included  
	      if (((rowloc != centerrow) || (colloc != centercol)) && 
		                    (bigdem[rowloc+(numrows+2)*colloc] > missingvalue))
	      {
		  cell_water_elev = bigdem[rowloc+(numrows+2)*colloc] + bigwater[rowloc+(numrows+2)*colloc];
		  center_water_elev = bigdem[centerrow+(numrows+2)*centercol] + bigwater[centerrow+(numrows+2)*centercol];
		  ht_diff =  center_water_elev - cell_water_elev;
		  if (ht_diff > 0)
		  {
		    if (bigdem[centerrow+(numrows+2)*centercol] > cell_water_elev) 
		    {
		      flow = bigwater[centerrow+(numrows+2)*centercol]/8.0;
		    }
		    else
		    {
		      flow = ht_diff/8.0;
		    }
		    flow = mini(maxi(flow, 0.0), bigwater[centerrow+(numrows+2)*centercol]);	 
		    bigwater[centerrow+(numrows+2)*centercol] = maxi(bigwater[centerrow+(numrows+2)*centercol] - flow, 0.0);
		    bigwater[rowloc+(numrows+2)*colloc] = bigwater[rowloc+(numrows+2)*colloc] + flow;
		  }
	      }
	  }
      }
      
}

void runoffsubtract(__global double *bigwater, __global double *bigdem, int centerrow, 
                             int centercol, double missingvalue, const int numrows) {
    int rowloc, colloc;
    double ht_diff, flow;
    
      for (rowloc=centerrow-1; rowloc<=centerrow+1; rowloc++){
	  for (colloc=centercol-1; colloc<=centercol+1; colloc++){
	  // make sure centre element is not included      
	      if (((rowloc != centerrow) || (colloc != centercol)) && 
		                    (bigdem[rowloc+(numrows+2)*colloc] > missingvalue)){
		  ht_diff =  (bigdem[centerrow+(numrows+2)*centercol] + bigwater[centerrow+(numrows+2)*centercol])-
		                               (bigdem[rowloc+(numrows+2)*colloc] + bigwater[rowloc+(numrows+2)*colloc]);
		  if (ht_diff > 0) {
		    if (bigdem[centerrow+(numrows+2)*centercol] > (bigdem[rowloc+(numrows+2)*colloc]+bigwater[rowloc+(numrows+2)*colloc])) {
		      flow = bigwater[centerrow+(numrows+2)*centercol]/8.0;
		    }
		    else
		    {
		      flow = ((bigdem[centerrow+(numrows+2)*centercol] - bigdem[rowloc+(numrows+2)*colloc]) + 
			      (bigwater[centerrow+(numrows+2)*centercol] - bigwater[rowloc+(numrows+2)*colloc]))/8.0;
//		      flow = ht_diff/8.0;
		    }
		    flow = mini(flow, bigwater[centerrow+(numrows+2)*centercol]);
		    bigwater[centerrow+(numrows+2)*centercol] = bigwater[centerrow+(numrows+2)*centercol] - flow;
		    bigwater[rowloc+(numrows+2)*colloc] = bigwater[rowloc+(numrows+2)*colloc] + flow; 
		  }
	      }   
	  }
      }
      
}

void runoffdrain(__global double *bigwater, __global double *bigdem, int centerrow, 
                int centercol, double missingvalue, __global double *totaldrain, 
                const int numrows, const int drainrow, const int draincol) {
    int rowloc, colloc;
    double ht_diff, center_water_elev, cell_water_elev, flow;
    
      for (rowloc=centerrow-1; rowloc<=centerrow+1; rowloc++){
	  for (colloc=centercol-1; colloc<=centercol+1; colloc++){
	  // make sure centre element is not included      
	    if (((rowloc != centerrow) || (colloc != centercol)) && 
		                    (bigdem[rowloc+(numrows+2)*colloc] > missingvalue)){
		  center_water_elev =  bigdem[centerrow+(numrows+2)*centercol] + bigwater[centerrow+(numrows+2)*centercol];
		  cell_water_elev = bigdem[rowloc+(numrows+2)*colloc] + bigwater[rowloc+(numrows+2)*colloc];	
	         // check for drain
	         if((colloc == draincol) && (rowloc == drainrow)){
		    // drain all water in center cell and edge cell
		    totaldrain[0]=totaldrain[0]+bigwater[drainrow+(numrows+2)*draincol]+bigwater[centerrow+(numrows+2)*centercol];
		    bigwater[drainrow+(numrows+2)*draincol] = 0.0;
		    bigwater[centerrow+(numrows+2)*centercol] = 0.0;
		 }
	 	 else
		 {	      
		    ht_diff =  center_water_elev - cell_water_elev;
		    if (ht_diff > 0) {
		      if (bigdem[centerrow+(numrows+2)*centercol] > cell_water_elev) {
			flow = bigwater[centerrow+(numrows+2)*centercol]/8.0;
		      }
		      else
		      {
			flow = ((bigdem[centerrow+(numrows+2)*centercol] - bigdem[rowloc+(numrows+2)*colloc]) + 
				(bigwater[centerrow+(numrows+2)*centercol] - bigwater[rowloc+(numrows+2)*colloc]))/8.0;
		      }
		      flow = mini(maxi(flow, 0.0), bigwater[centerrow+(numrows+2)*centercol]);
		      bigwater[centerrow+(numrows+2)*centercol] = maxi(bigwater[centerrow+(numrows+2)*centercol] - flow, 0.0);
		      bigwater[rowloc+(numrows+2)*colloc] = bigwater[rowloc+(numrows+2)*colloc] + flow; 
		    }
		 }
	      }   
	  }
      }
      
}


__kernel void add(__global double *bigwater, __global double *bigdem, const double missingvalue, 
		  const int numrows, const int numcols, const int offset, const int oi, const int oj){

    int row, col;
    int row1 = get_global_id(0);
    int col1 = get_global_id(1);  
    int off = offset-1;
    row = (oi-off)+off*row1;
    col = (oj-off)+off*col1;
    if (row>=1 && row<=numrows && col>=1 && col<=numcols && 
	bigwater[row+(numrows+2)*col]>0.0 && bigdem[row+(numrows+2)*col]>missingvalue ){
	runoffadd(bigwater,bigdem,row,col,missingvalue,numrows);
    }
}


__kernel void subtract(__global double *bigwater, __global double *bigdem, const double missingvalue, 
		       const int numrows, const int numcols, const int offset, const int oi, const int oj){

    int row, col;
    int row1 = get_global_id(0);
    int col1 = get_global_id(1);  
    int off = offset-1;
    row = (oi-off)+off*row1;
    col = (oj-off)+off*col1;
    if (row>=1 && row<=numrows && col>=1 && col<=numcols && 
	  bigwater[row+(numrows+2)*col]>0.0 && bigdem[row+(numrows+2)*col]>missingvalue){
	runoffsubtract(bigwater,bigdem,row,col,missingvalue,numrows); 
    }
}



__kernel void ddrain(__global double *bigwater, __global double *bigdem, double missingvalue,
		     const int numrows,  const int numcols, const int offset, const int oi, 
		     const int oj, __global double *totaldrain, const int drainrow, const int draincol){
  
  
    int row, col;
    int row1 = get_global_id(0);
    int col1 = get_global_id(1);  
    int off = offset-1;
    row = (oi-off)+off*row1;
    col = (oj-off)+off*col1;
    if (row>=1 && row<=numrows && col>=1 && col<=numcols && 
          bigwater[row+(numrows+2)*col] > 0.0 && (bigdem[row+(numrows+2)*col] > missingvalue)
	  && (row != drainrow || col !=draincol )){
	 runoffdrain(bigwater,bigdem,row,col,missingvalue,totaldrain,numrows,drainrow,draincol);                      
    }
}