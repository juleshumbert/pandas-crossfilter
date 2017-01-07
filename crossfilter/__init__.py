import uuid
from IPython.display import HTML, Javascript, display


def load_resources():
    display(Javascript("""require.config({
    paths: {
        'd3': 'https://cdnjs.cloudflare.com/ajax/libs/d3/3.5.16/d3.min',
        'crossfilter': 'https://cdnjs.cloudflare.com/ajax/libs/crossfilter/1.3.12/crossfilter.min',
        'dc': 'https://cdnjs.cloudflare.com/ajax/libs/dc/2.0.0-beta.32/dc',
    },
    shim: {
        'crossfilter': {
            deps: [],
            exports: 'crossfilter'
        }
    }
});"""), HTML('<link href="https://cdnjs.cloudflare.com/ajax/libs/dc/1.7.5/dc.min.css" rel="stylesheet" type="text/css">'))



def dataframe_as_js(df, name='crossfilterData'):
    return Javascript("window.{name} = {json};".format(name=name, json=df.to_json(orient='records')))



class Crossfilter:
    def __init__(self, df, graph_types, axes, reducers, dim_reducer, sizes, graphs=None, html_file_name='crossfilter'):
        self.df = df
        self.graphs = graphs
        self.html_file_name = html_file_name
        if not self.graphs:
            self.graphs = [self.default_graph(ax, gr, red, dim_red, s) for (ax, gr, red, dim_red, s) in zip(axes, graph_types, reducers, dim_reducer, sizes)]

    def default_graph(self, axes, graph_type, red, dim_red, s):
        if graph_type == 'TimeChart':
            return TimeChart(axes, red, dim_red, width=s[0], height=s[1])
        elif graph_type == 'RowChart':
            return RowChart(axes, red, dim_red, width=s[0], height=s[1])
        elif graph_type == 'BarChart':
            return BarChart(axes, red, dim_red, width=s[0], height=s[1])
        elif graph_type == 'LineChart':
            return LineChart(axes, red, dim_red, width=s[0], height=s[1])
        elif graph_type == 'ScatterPlot':
            return ScatterPlot(axes, red, dim_red, width=s[0], height=s[1])
        elif graph_type == 'ScatterPlotTime':
            return ScatterPlotTime(axes, red, dim_red, width=s[0], height=s[1])
        elif graph_type == 'PieChart':
            return PieChart(axes, red, dim_red, width=s[0], height=s[1])

    def _repr_javascript_(self):
        guid = uuid.uuid4()
        df = self.df.copy()
        # convert category columns back to string before calling to_json
        # https://github.com/pydata/pandas/pull/10321
        for i, s in df.loc[:, df.select_dtypes(include=['category']).columns].iteritems():
            df.loc[:, i] = s.astype('str')
        js = """
    require(['d3', 'crossfilter', 'dc'], function(d3, crossfilter, dc) {
        var pluck = function(prop) {
            return function(d) { return d[prop]; };
        };
        var pluck2 = function(prop1, prop2, prop3) {
            return function(d) { return [+d[prop1], +d[prop2], +d[prop3]]; };
        };
        
        var crossfilterData = {json};
        var cf = crossfilter(crossfilterData);"""
        js += Summary()._repr_javascript_()
        for graph in self.graphs:
            js += graph._repr_javascript_()
        js += """
        dc.renderAll();
        dc.redrawAll();
    });"""

        with open(self.html_file_name+".html", "w") as text_file:
            html = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8" />
<title>pandas-crossfilter</title>

<script src="https://cdnjs.cloudflare.com/ajax/libs/require.js/2.1.10/require.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/2.0.3/jquery.min.js"></script>
<div id="{uuid}"></div>
<script type="text/javascript">
var element = $('#{uuid}');
require.config({
    paths: {
        'd3': 'https://cdnjs.cloudflare.com/ajax/libs/d3/3.5.16/d3.min',
        'crossfilter': 'https://cdnjs.cloudflare.com/ajax/libs/crossfilter/1.3.12/crossfilter.min',
        'dc': 'https://cdnjs.cloudflare.com/ajax/libs/dc/2.0.0-beta.32/dc',
    },
    shim: {
        'crossfilter': {
            deps: [],
            exports: 'crossfilter'
        }
    }
});
</script>
<link href="https://cdnjs.cloudflare.com/ajax/libs/dc/1.7.5/dc.min.css" rel="stylesheet" type="text/css">'
<script> 
""".replace('{uuid}', str(guid))
            html += js.replace('{json}', df.to_json(orient='records')).replace('{uuid}', str(guid))
            html += """</script>
</html>
"""
            text_file.write(html)
        self.df.to_csv(self.html_file_name+".csv", index=False)
        self.df.to_csv(self.html_file_name+".json", orient='records')
        return js.replace('{json}', df.to_json(orient='records', date_unit='ms')).replace('{uuid}', str(guid))



class Chart(object):
    def __init__(self, crossfilter_name='cf'):
        self.crossfilter_name = crossfilter_name

    def _repr_javascript_(self):
        pass


class Summary(Chart):
    def _repr_javascript_(self):
        return """
        var all = {cf}.groupAll();
        element.append('<div id="dc-{uuid}-count"><strong class="filter-count">?</strong> selected ' +
                       'out of <strong class="total-count">?</strong> records</div>' +
                       '<div style="clear: both;"></div>');
        var count = dc.dataCount("#dc-{uuid}-count");
        count.dimension({cf}).group(all);""".replace('{cf}', self.crossfilter_name)


class ProperyChart(Chart):
    def __init__(self, property, reducer, dim_reducer, crossfilter_name='cf', width=450, height=250):
        super(ProperyChart, self).__init__(crossfilter_name)
        self.property = property
        self.reducer = reducer
        self.dim_reducer= dim_reducer
        self.width = width
        self.height = height
        self.reducerjs = self.return_reducer()
        self.value_accessorjs = self.return_value_accessor()

    def return_value_accessor(self):
        if self.reducer == 'None':
            return ''
        elif self.reducer == 'Count':
            return ''
        elif self.reducer == 'Sum':
            return ''
        elif self.reducer == 'Mean':
            return '.valueAccessor(function (p) {return p.value.averages;});'
        elif self.reducer == 'CumulativeSum':
            return '.valueAccessor(function (p) {return p.value;});'
        elif self.reducer == 'CumulativeCount':
            return '.valueAccessor(function (p) {return p.value;});'

    def return_reducer(self):
        if self.reducer == 'None':
            return 'var group = dim.group()'
        elif self.reducer == 'Count':
            return 'var group = dim.group().reduceCount()'
        elif self.reducer == 'Sum':
            return 'var group = dim.group().reduceSum(function(d) {return d["{dim_reducer}"];})'.replace('{dim_reducer}', self.dim_reducer)

        elif self.reducer == 'Mean':
            return """ var group = dim.group().reduce(
function(p,v) {
      ++p.count
      p.sums += v["{dim_reducer}"];
      p.averages = (p.count === 0) ? 0 : p.sums/p.count; 
    return p;
  }, 
function(p,v) {
      --p.count
      p.sums -= v["{dim_reducer}"];
      p.averages = (p.count === 0) ? 0 : p.sums/p.count;
    return p;
  },
function reduceInitAvg() {
  return {count:0, sums:0, averages:0};
} )""".replace('{dim_reducer}', self.dim_reducer)

        elif self.reducer == 'CumulativeCount':
            return """var _group = dim.group().reduceCount(); 
var group = { 
    all:function () { 
     var cumulate = 0; 
     var g = []; 
     _group.all().forEach(function(d,i) { 
       cumulate += d.value; 
       g.push({key:d.key,value:cumulate}) 
     }); 
     return g; 
    } 
  }; """
        elif self.reducer == 'CumulativeSum':
            return """var _group = dim.group().reduceSum(function(d) {return +d["{dim_reducer}"];}); 
var group = { 
    all:function () { 
     var cumulate = 0; 
     var g = []; 
     _group.all().forEach(function(d,i) { 
       cumulate += d.value; 
       g.push({key:d.key,value:cumulate}) 
     }); 
     return g; 
    } 
  }; """.replace('{dim_reducer}', self.dim_reducer)

class BarChart(ProperyChart):
    def _repr_javascript_(self):
        return """
        var prop = "{prop}";
        var propId = prop.replace(".", "_") + "_" + "{reducer}";
        var chartId = "dc-{uuid}-chart-" + propId;
        element.append('<div style="float: left;" id="' + chartId + '"><strong>' + prop + '</strong>' +
                       '<div style="clear: both;"></div></div>');
        var dim = {cf}.dimension(pluck(prop));
        {reducerjs}
        var min = dim.bottom(1)[0][prop];
        var max = dim.top(1)[0][prop] + 1;
        var chart = dc.barChart("#" + chartId);
        chart.dimension(dim).group(group)
            .x(d3.scale.linear().domain([min, max]))
            .xUnits(dc.units.integers)
            .elasticY(true)
            .width({width}).height({height}){valAcc};
        """.replace('{cf}', self.crossfilter_name).replace("{prop}", self.property)\
            .replace('{width}', str(self.width)).replace('{height}', str(self.height))\
             .replace('{reducerjs}', self.reducerjs).replace('{valAcc}', self.value_accessorjs).replace('{reducer}', self.reducer)


class RowChart(ProperyChart):
    def _repr_javascript_(self):
        return """
        var prop = "{prop}";
        var propId = prop.replace(".", "_")  + "_" + "{reducer}";
        var chartId = "dc-{uuid}-chart-" + propId;
        element.append('<div style="float: left;" id="' + chartId + '"><strong>' + prop + '</strong>' +
                       '<div style="clear: both;"></div></div>');
        var dim = {cf}.dimension(pluck(prop));
        {reducerjs}
        var min = dim.bottom(1)[0][prop];
        var max = dim.top(1)[0][prop] + 1;
        var chart = dc.rowChart("#" + chartId);
        chart.dimension(dim).group(group).width({width}).height({height}).elasticX(true){valAcc};
        """.replace('{cf}', self.crossfilter_name).replace("{prop}", self.property)\
            .replace('{width}', str(self.width)).replace('{height}', str(self.height))\
.replace('{reducerjs}', self.reducerjs).replace('{valAcc}', self.value_accessorjs).replace('{reducer}', self.reducer)

class ScatterPlot(ProperyChart):
    def _repr_javascript_(self):
        return """

        var prop1 = "{prop1}";
        var prop2 = "{prop2}";
        var prop3 = "{prop3}";
        var propId = prop1.replace(".", "_")+"___"+prop2.replace(".", "_")+"___"+prop3.replace(".", "_")+  "_" +"{reducer}";
        var chartId = "dc-{uuid}-chart-" + propId;
        var catColors = d3.scale.ordinal()
                  .domain([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
                  .range(["#ff2600", "#ffdd00", "#9dff00", "#00d4ff", "#1500ff", "#6a00ff", "#e900ff", "#000000", "#770000", "#ff7700"]);
        element.append('<div style="float: left;" id="' + chartId + '"><strong>' +propId+ '</strong>' +
                       '<div style="clear: both;"></div></div>');
        var dim = {cf}.dimension(pluck2(prop1, prop2, prop3));
        {reducerjs}
        var min = dim.bottom(1)[0][prop1];
        var max = dim.top(1)[0][prop1] + 1;
        var chart = dc.scatterPlot("#" + chartId);
        chart.dimension(dim).group(group)
            .x(d3.scale.linear().domain([min, max]))
            .elasticY(true)
            .elasticX(true)
            .margins({top: 20, right: 40, bottom: 20, left: 40})
            .width({width}).height({height})
  .existenceAccessor(function(d) {
    return d.value > 0;
  })
  .colorAccessor(function(d) {
    return d.key[2];
  })
          .colors(catColors)
          .filterHandler(function(dim, filters) {
                if(!filters || !filters.length)
                    dim.filter(null);
                else {
                    dim.filterFunction(function(d) {
                        return filters[0].isFiltered([d[0],d[1]]);
                      })
                }
          })
        """.replace('{cf}', self.crossfilter_name).replace("{prop1}", self.property[0]).replace("{prop2}", self.property[1])\
    .replace("{prop3}", self.property[2])\
            .replace('{width}', str(self.width)).replace('{height}', str(self.height))\
    .replace('{reducerjs}', self.reducerjs).replace('{valAcc}', self.value_accessorjs).replace('{reducer}', self.reducer)
  

class ScatterPlotTime(ProperyChart):
    def _repr_javascript_(self):
        return """

        var prop1 = "{prop1}";
        var prop2 = "{prop2}";
        var prop3 = "{prop3}";
        var propId = prop1.replace(".", "_")+"___"+prop2.replace(".", "_")+"___"+prop3.replace(".", "_")+  "_" +"{reducer}";
        var chartId = "dc-{uuid}-chart-" + propId;
        var catColors = d3.scale.ordinal()
                  .domain([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
                  .range(["#ff2600", "#ffdd00", "#9dff00", "#00d4ff", "#1500ff", "#6a00ff", "#e900ff", "#000000", "#770000", "#ff7700"]);
        element.append('<div style="float: left;" id="' + chartId + '"><strong>' +propId+ '</strong>' +
                       '<div style="clear: both;"></div></div>');
        var dim = {cf}.dimension(pluck2(prop1, prop2, prop3));
        {reducerjs}
        var min = dim.bottom(1)[0][prop1];
        var max = dim.top(1)[0][prop1] + 1;
        var chart = dc.scatterPlot("#" + chartId);
        chart.dimension(dim).group(group)
            .x(d3.time.scale().domain([Date(min), Date(max)]))
            .elasticY(true)
            .elasticX(true)
            .margins({top: 20, right: 40, bottom: 20, left: 40})
            .width({width}).height({height})
  .existenceAccessor(function(d) {
    return d.value > 0;
  })
  .colorAccessor(function(d) {
    return d.key[2];
  })
          .colors(catColors)
          .filterHandler(function(dim, filters) {
                if(!filters || !filters.length)
                    dim.filter(null);
                else {
                    dim.filterFunction(function(d) {
                        return filters[0].isFiltered([d[0],d[1]]);
                      })
                }
          })
        """.replace('{cf}', self.crossfilter_name).replace("{prop1}", self.property[0]).replace("{prop2}", self.property[1])\
    .replace("{prop3}", self.property[2])\
            .replace('{width}', str(self.width)).replace('{height}', str(self.height))\
    .replace('{reducerjs}', self.reducerjs).replace('{valAcc}', self.value_accessorjs).replace('{reducer}', self.reducer)
  
            
class LineChart(ProperyChart):
    def _repr_javascript_(self):
        return """
        var prop = "{prop}";
        var propId = prop.replace(".", "_") + "_" + "{reducer}";
        var chartId = "dc-{uuid}-chart-" + propId;
        element.append('<div style="float: left;" id="' + chartId + '"><strong>' + prop + '</strong>' +
                       '<div style="clear: both;"></div></div>');
        var dim = {cf}.dimension(pluck(prop));
        {reducerjs}
        var min = dim.bottom(1)[0][prop];
        var max = dim.top(1)[0][prop] + 1;
        var chart = dc.lineChart("#" + chartId);
        chart.dimension(dim).group(group)
            .x(d3.time.scale().domain([min, max]))
            .elasticY(true)
            .elasticX(true)
            .renderArea(true)
            .width({width}).height({height}){valAcc};
        """.replace('{cf}', self.crossfilter_name).replace("{prop}", self.property)\
            .replace('{width}', str(self.width)).replace('{height}', str(self.height))\
    .replace('{reducerjs}', self.reducerjs).replace('{valAcc}', self.value_accessorjs).replace('{reducer}', self.reducer)
 

    
# crossfilterData.forEach(function (d) {
 #           d[prop] = new Date(d[prop]);
#      });
 #     var cf = crossfilter(crossfilterData)
class TimeChart(ProperyChart):

    def _repr_javascript_(self):
        return """
        var prop = "{prop}";

        var propId = prop.replace(".", "_") + "_" + "{reducer}";
        var chartId = "dc-{uuid}-chart-" + propId;
        element.append('<div style="float: left;" id="' + chartId + '"><strong>' + prop + '</strong>' +
                       '<div style="clear: both;"></div></div>');
        var dim = {cf}.dimension(pluck(prop));
        {reducerjs}

        
        var min = dim.bottom(1)[0][prop];
        var max = dim.top(1)[0][prop] + 1;
        var chart = dc.barChart("#" + chartId);
        chart.dimension(dim).group(group)
            .x(d3.time.scale().domain([Date(min), Date(max)]))
            .elasticY(true)
            .elasticX(true)
            .width({width}).height({height}){valAcc};
        """.replace('{cf}', self.crossfilter_name).replace("{prop}", self.property)\
            .replace('{width}', str(self.width)).replace('{height}', str(self.height))\
    .replace('{reducerjs}', self.reducerjs).replace('{valAcc}', self.value_accessorjs).replace('{reducer}', self.reducer)
    

class PieChart(ProperyChart):
    def _repr_javascript_(self):
        return """
        var prop = "{prop}";
        var propId = prop.replace(".", "_") + "_" + "{reducer}";
        var chartId = "dc-{uuid}-chart-" + propId;
        element.append('<div style="float: left;" id="' + chartId + '"><strong>' + prop + '</strong>' +
                       '<div style="clear: both;"></div></div>');
        var dim = {cf}.dimension(pluck(prop));
        {reducerjs}
        var min = dim.bottom(1)[0][prop];
        var max = dim.top(1)[0][prop] + 1;
        var chart = dc.pieChart("#" + chartId);
        chart.dimension(dim).group(group){valAcc};
        """.replace('{cf}', self.crossfilter_name).replace("{prop}", self.property)\
            .replace('{width}', str(self.width)).replace('{height}', str(self.height))\
.replace('{reducerjs}', self.reducerjs).replace('{valAcc}', self.value_accessorjs).replace('{reducer}', self.reducer)

